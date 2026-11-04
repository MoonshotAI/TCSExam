// nurse-inrc baseline solver: INRC-I nurse rostering.
//
// Reads an INRC-I instance (XML, <SchedulingPeriod>) on stdin and writes a
// roster (XML, <Solution>) on stdout. The roster must cover the demand
// EXACTLY (per day and shift type) and give every nurse at most one shift
// per day; the judge recomputes the soft-constraint penalty from scratch.
//
// Baseline algorithm (deliberately simple): penalty-aware greedy
// construction, then a short simulated annealing over four coverage-
// preserving move types with a fixed iteration count. Fixed seed + fixed
// work program -> deterministic.
//
// The per-instance wall-clock budget (seconds) is handed over via env
// NURSE_INSTANCE_SECONDS (NURSE_TIME_POOL carries the same value for
// backward compatibility).
#include <algorithm>
#include <chrono>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <iostream>
#include <iterator>
#include <map>
#include <random>
#include <set>
#include <string>
#include <vector>

// ---------------------------------------------------------------------------
// Minimal XML reader (enough for the fixed INRC-I schema)
// ---------------------------------------------------------------------------
struct XmlNode {
    std::string tag;
    std::map<std::string, std::string> attr;
    std::string text;
    std::vector<XmlNode> kids;
    const XmlNode* find(const std::string& t) const {
        for (const auto& k : kids) if (k.tag == t) return &k;
        return nullptr;
    }
    std::string findText(const std::string& t) const {
        const XmlNode* n = find(t);
        return n ? n->text : "";
    }
};

static void skipWs(const std::string& s, size_t& p) {
    while (p < s.size() && isspace((unsigned char)s[p])) p++;
}

static bool parseNode(const std::string& s, size_t& p, XmlNode& out) {
    skipWs(s, p);
    if (p >= s.size() || s[p] != '<') return false;
    p++;
    if (p < s.size() && (s[p] == '?' || s[p] == '!')) {  // prolog/comment/doctype
        while (p < s.size() && s[p] != '>') p++;
        if (p < s.size()) p++;
        return parseNode(s, p, out);
    }
    size_t b = p;
    while (p < s.size() && !isspace((unsigned char)s[p]) && s[p] != '>' && s[p] != '/') p++;
    out.tag = s.substr(b, p - b);
    // attributes
    for (;;) {
        skipWs(s, p);
        if (p >= s.size()) return false;
        if (s[p] == '/' && p + 1 < s.size() && s[p + 1] == '>') { p += 2; return true; }
        if (s[p] == '>') { p++; break; }
        size_t kb = p;
        while (p < s.size() && s[p] != '=' && !isspace((unsigned char)s[p])) p++;
        std::string key = s.substr(kb, p - kb);
        skipWs(s, p);
        if (p >= s.size() || s[p] != '=') return false;
        p++;
        skipWs(s, p);
        if (p >= s.size() || (s[p] != '"' && s[p] != '\'')) return false;
        char q = s[p++];
        size_t vb = p;
        while (p < s.size() && s[p] != q) p++;
        out.attr[key] = s.substr(vb, p - vb);
        if (p < s.size()) p++;
    }
    // content
    for (;;) {
        skipWs(s, p);
        if (p >= s.size()) return false;
        if (s.compare(p, 2, "</") == 0) {
            p += 2;
            while (p < s.size() && s[p] != '>') p++;
            if (p < s.size()) p++;
            return true;
        }
        if (s[p] == '<') {
            XmlNode kid;
            if (!parseNode(s, p, kid)) return false;
            out.kids.push_back(std::move(kid));
        } else {
            size_t tb = p;
            while (p < s.size() && s[p] != '<') p++;
            std::string t = s.substr(tb, p - tb);
            size_t a = t.find_first_not_of(" \t\r\n");
            size_t z = t.find_last_not_of(" \t\r\n");
            if (a != std::string::npos) out.text += t.substr(a, z - a + 1);
        }
    }
}

// ---------------------------------------------------------------------------
// Instance model
// ---------------------------------------------------------------------------
static const int UU = 0x3FFFFFFF;

struct Cond {
    std::vector<int> numbering;
    int last_nr_history = UU, future_nr = UU;
    int max_total = -1, min_total = -1, max_between = -1, min_between = -1;
    int max_consecutive = -1, min_consecutive = -1;
    int cost_max_total = 0, cost_min_total = 0, cost_max_between = 0, cost_min_between = 0;
    int cost_max_consecutive = 0, cost_min_consecutive = 0;
    std::vector<int> max_pert, min_pert, cost_max_pert, cost_min_pert;
    Cond(int n = 0) : numbering(n, UU), max_pert(n, 0), min_pert(n, 0),
                      cost_max_pert(n, 0), cost_min_pert(n, 0) {}
};

struct Pattern { int weight; std::vector<std::pair<std::string, std::string>> entries; };

struct Contract {
    int maxAssignOn = 0, maxAssignW = 0, maxAssignV = 0;
    int minAssignOn = 0, minAssignW = 0, minAssignV = 0;
    int maxCwdOn = 0, maxCwdW = 0, maxCwdV = 0;
    int minCwdOn = 0, minCwdW = 0, minCwdV = 0;
    int maxCfdOn = 0, maxCfdW = 0, maxCfdV = 0;
    int minCfdOn = 0, minCfdW = 0, minCfdV = 0;
    int maxCwwOn = 0, maxCwwW = 0, maxCwwV = 0;
    int minCwwOn = 0, minCwwW = 0, minCwwV = 0;
    int completeOn = 0, completeW = 0;
    int identOn = 0, identW = 0;
    int altSkillOn = 0, altSkillW = 0;
    std::string weekendDef = "SaturdaySunday";
    std::vector<std::string> patternIds;
};

struct Instance {
    std::string id;
    int numDays = 0;
    std::vector<std::string> dateStr;          // day index -> YYYY-MM-DD
    std::vector<int> weekday;                  // day index -> 0=Mon..6=Sun
    std::vector<std::string> shifts;           // shift IDs, XML order
    std::map<std::string, int> shiftIndex;
    std::vector<std::set<std::string>> shiftSkills;
    std::map<std::string, Pattern> patterns;
    std::map<std::string, Contract> contracts;
    std::vector<std::string> emps;
    std::map<std::string, int> empIndex;
    std::vector<int> empContract;              // employee idx -> contract idx
    std::vector<std::string> contractIds;
    std::vector<std::set<std::string>> empSkills;
    std::map<std::pair<int,int>, int> cover;   // (day, shift idx) -> required
    std::vector<std::vector<std::pair<int,int>>> dayOff;     // emp -> (day, weight)
    std::vector<std::vector<std::tuple<int,int,int>>> shiftOff; // emp -> (day, shift, weight)
    int firstSaturday = -1, numWeekends = 0;
};

static int daysFromCivil(int y, unsigned m, unsigned d) {
    y -= m <= 2;
    const int era = (y >= 0 ? y : y - 399) / 400;
    const unsigned yoe = (unsigned)(y - era * 400);
    const unsigned doy = (153 * (m + (m > 2 ? -3 : 9)) + 2) / 5 + d - 1;
    const unsigned doe = yoe * 365 + yoe / 4 - yoe / 100 + doy;
    return era * 146097 + (int)doe - 719468;
}

static int weekdayOf(int z) {  // 0=Monday..6=Sunday; 1970-01-01 (z=0) was Thursday
    int wd = (z + 3) % 7;
    if (wd < 0) wd += 7;
    return wd;
}

static void parseDate(const std::string& s, int& y, int& m, int& d) {
    y = atoi(s.substr(0, 4).c_str());
    m = atoi(s.substr(5, 2).c_str());
    d = atoi(s.substr(8, 2).c_str());
}

static bool parseOnWeightValue(const XmlNode* c, const char* tag, int& on, int& w, int& v) {
    const XmlNode* el = c->find(tag);
    if (!el) { on = 0; w = 0; v = 0; return false; }
    auto onA = el->attr.find("on");
    auto wA = el->attr.find("weight");
    on = (onA != el->attr.end() && (onA->second == "1" || onA->second == "true")) ? 1 : 0;
    w = (wA != el->attr.end()) ? atoi(wA->second.c_str()) : 0;
    v = atoi(el->text.c_str());
    return true;
}

static void parseFlagWeight(const XmlNode* c, const char* tag, int& on, int& w) {
    const XmlNode* el = c->find(tag);
    if (!el) { on = 0; w = 0; return; }
    on = (el->text == "true" || el->text == "1") ? 1 : 0;
    auto wA = el->attr.find("weight");
    w = (wA != el->attr.end()) ? atoi(wA->second.c_str()) : 0;
}

static Instance loadInstance(const std::string& xml) {
    size_t p = 0;
    XmlNode root;
    if (!parseNode(xml, p, root) || root.tag != "SchedulingPeriod") {
        fprintf(stderr, "bad instance XML\n");
        exit(2);
    }
    Instance sp;
    sp.id = root.attr.count("ID") ? root.attr.at("ID") : "";
    std::string sd = root.findText("StartDate"), ed = root.findText("EndDate");
    int y1, m1, d1, y2, m2, d2;
    parseDate(sd, y1, m1, d1);
    parseDate(ed, y2, m2, d2);
    int z1 = daysFromCivil(y1, m1, d1), z2 = daysFromCivil(y2, m2, d2);
    sp.numDays = z2 - z1 + 1;
    for (int i = 0; i < sp.numDays; i++) {
        int z = z1 + i;
        // back to civil
        int zz = z + 719468;
        int era = (zz >= 0 ? zz : zz - 146096) / 146097;
        unsigned doe = (unsigned)(zz - era * 146097);
        unsigned yoe = (doe - doe / 1460 + doe / 36524 - doe / 146096) / 365;
        int y = (int)yoe + era * 400;
        unsigned doy = doe - (365 * yoe + yoe / 4 - yoe / 100);
        unsigned mp = (5 * doy + 2) / 153;
        unsigned d = doy - (153 * mp + 2) / 5 + 1;
        unsigned m = mp + (mp < 10 ? 3 : -9);
        char buf[16];
        snprintf(buf, sizeof buf, "%04d-%02u-%02u", y + (m <= 2), m, d);
        sp.dateStr.push_back(buf);
        sp.weekday.push_back(weekdayOf(z));
    }
    for (int i = 0; i < std::min(7, sp.numDays); i++)
        if (sp.weekday[i] == 5) { sp.firstSaturday = i; break; }
    for (int nn = sp.firstSaturday; 0 <= nn && nn < sp.numDays; nn += 7) sp.numWeekends++;

    const XmlNode* sts = root.find("ShiftTypes");
    for (const auto& sh : sts->kids) {
        std::string sid = sh.attr.at("ID");
        sp.shiftIndex[sid] = (int)sp.shifts.size();
        sp.shifts.push_back(sid);
        std::set<std::string> sks;
        if (const XmlNode* sk = sh.find("Skills"))
            for (const auto& e : sk->kids) sks.insert(e.text);
        sp.shiftSkills.push_back(std::move(sks));
    }
    if (const XmlNode* pats = root.find("Patterns")) {
        for (const auto& pn : pats->kids) {
            Pattern pat;
            pat.weight = atoi(pn.attr.at("weight").c_str());
            if (const XmlNode* pes = pn.find("PatternEntries"))
                for (const auto& e : pes->kids)
                    pat.entries.push_back({e.findText("ShiftType"), e.findText("Day")});
            sp.patterns[pn.attr.at("ID")] = pat;
        }
    }
    const XmlNode* cons = root.find("Contracts");
    for (const auto& cn : cons->kids) {
        Contract ct;
        parseOnWeightValue(&cn, "MaxNumAssignments", ct.maxAssignOn, ct.maxAssignW, ct.maxAssignV);
        parseOnWeightValue(&cn, "MinNumAssignments", ct.minAssignOn, ct.minAssignW, ct.minAssignV);
        parseOnWeightValue(&cn, "MaxConsecutiveWorkingDays", ct.maxCwdOn, ct.maxCwdW, ct.maxCwdV);
        parseOnWeightValue(&cn, "MinConsecutiveWorkingDays", ct.minCwdOn, ct.minCwdW, ct.minCwdV);
        parseOnWeightValue(&cn, "MaxConsecutiveFreeDays", ct.maxCfdOn, ct.maxCfdW, ct.maxCfdV);
        parseOnWeightValue(&cn, "MinConsecutiveFreeDays", ct.minCfdOn, ct.minCfdW, ct.minCfdV);
        parseOnWeightValue(&cn, "MaxConsecutiveWorkingWeekends", ct.maxCwwOn, ct.maxCwwW, ct.maxCwwV);
        parseOnWeightValue(&cn, "MinConsecutiveWorkingWeekends", ct.minCwwOn, ct.minCwwW, ct.minCwwV);
        parseFlagWeight(&cn, "CompleteWeekends", ct.completeOn, ct.completeW);
        parseFlagWeight(&cn, "IdenticalShiftTypesDuringWeekend", ct.identOn, ct.identW);
        parseFlagWeight(&cn, "AlternativeSkillCategory", ct.altSkillOn, ct.altSkillW);
        const XmlNode* wk = cn.find("WeekendDefinition");
        if (wk) ct.weekendDef = wk->text;
        if (const XmlNode* up = cn.find("UnwantedPatterns"))
            for (const auto& pe : up->kids) ct.patternIds.push_back(pe.text);
        std::string cid = cn.attr.at("ID");
        sp.contracts[cid] = ct;
        sp.contractIds.push_back(cid);
    }
    const XmlNode* emps = root.find("Employees");
    for (const auto& en : emps->kids) {
        std::string eid = en.attr.at("ID");
        sp.empIndex[eid] = (int)sp.emps.size();
        sp.emps.push_back(eid);
        std::string cid = en.findText("ContractID");
        int ci = 0;
        for (size_t i = 0; i < sp.contractIds.size(); i++)
            if (sp.contractIds[i] == cid) { ci = (int)i; break; }
        sp.empContract.push_back(ci);
        std::set<std::string> sks;
        if (const XmlNode* sk = en.find("Skills"))
            for (const auto& e : sk->kids) sks.insert(e.text);
        sp.empSkills.push_back(std::move(sks));
        sp.dayOff.push_back({});
        sp.shiftOff.push_back({});
    }
    std::map<std::pair<std::string,std::string>, int> dow, spec;
    if (const XmlNode* cr = root.find("CoverRequirements")) {
        for (const auto& ch : cr->kids) {
            if (ch.tag == "DayOfWeekCover") {
                std::string dn = ch.findText("Day");
                for (const auto& cv : ch.kids)
                    if (cv.tag == "Cover")
                        dow[{dn, cv.findText("Shift")}] = atoi(cv.findText("Preferred").c_str());
            } else if (ch.tag == "DateSpecificCover") {
                std::string dt = ch.findText("Date");
                for (const auto& cv : ch.kids)
                    if (cv.tag == "Cover")
                        spec[{dt, cv.findText("Shift")}] = atoi(cv.findText("Preferred").c_str());
            }
        }
    }
    static const char* WN[7] = {"Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"};
    for (int di = 0; di < sp.numDays; di++) {
        std::string wn = WN[sp.weekday[di]];
        for (size_t si = 0; si < sp.shifts.size(); si++) {
            int req = 0;
            auto itS = spec.find({sp.dateStr[di], sp.shifts[si]});
            auto itD = dow.find({wn, sp.shifts[si]});
            if (itS != spec.end()) req = itS->second;
            else if (itD != dow.end()) req = itD->second;
            if (req) sp.cover[{(int)di, (int)si}] = req;
        }
    }
    auto parseReqs = [&](const char* tag, const char* sing, bool withShift) {
        const XmlNode* rr = root.find(tag);
        if (!rr) return;
        for (const auto& el : rr->kids) {
            if (el.tag != sing) continue;
            int w = el.attr.count("weight") ? atoi(el.attr.at("weight").c_str()) : 0;
            std::string eid = el.findText("EmployeeID");
            std::string dt = el.findText("Date");
            if (!sp.empIndex.count(eid)) continue;
            int yy, mm, dd;
            parseDate(dt, yy, mm, dd);
            int di = daysFromCivil(yy, mm, dd) - z1;
            if (di < 0 || di >= sp.numDays) continue;
            int ei = sp.empIndex[eid];
            if (withShift) {
                std::string st = el.findText("ShiftTypeID");
                if (!sp.shiftIndex.count(st)) continue;
                sp.shiftOff[ei].push_back({di, sp.shiftIndex[st], w});
            } else {
                sp.dayOff[ei].push_back({di, w});
            }
        }
    };
    parseReqs("DayOffRequests", "DayOff", false);
    parseReqs("ShiftOffRequests", "ShiftOff", true);
    return sp;
}

// ---------------------------------------------------------------------------
// Penalty evaluator — port of the official INRC-I numbering method
// (mirrors the Python checker the judge uses).
// ---------------------------------------------------------------------------
struct Evaluator {
    const Instance& sp;
    int D, S, size;
    // per-employee prebuilt conditions
    std::vector<std::vector<Cond>> conds;
    Evaluator(const Instance& inst) : sp(inst) {
        D = sp.numDays;
        S = (int)sp.shifts.size();
        size = D * S;
        for (size_t e = 0; e < sp.emps.size(); e++)
            conds.push_back(buildConds((int)e));
    }
    std::pair<int,int> weekendLayout(const Contract& ct) const {
        int begin = sp.firstSaturday, ln = 2;
        if (ct.weekendDef == "FridaySaturdaySunday") { begin -= 1; ln = 3; }
        else if (ct.weekendDef == "FridaySaturdaySundayMonday") { begin -= 1; ln = 4; }
        else if (ct.weekendDef == "SaturdaySundayMonday") { ln = 3; }
        return {begin, ln};
    }
    std::vector<Cond> buildConds(int e) const {
        const Contract& ct = sp.contracts.at(sp.contractIds[sp.empContract[e]]);
        std::vector<Cond> out;
        {  // working days
            Cond c(size);
            for (int i = 0; i < size; i++) c.numbering[i] = i / S;
            if (ct.maxCwdOn) { c.max_consecutive = ct.maxCwdV; c.cost_max_consecutive = ct.maxCwdW; }
            if (ct.minCwdOn) { c.min_consecutive = ct.minCwdV; c.cost_min_consecutive = ct.minCwdW; }
            out.push_back(c);
        }
        {  // free days
            Cond c(size);
            for (int i = 0; i < size; i++) c.numbering[i] = i / S;
            c.last_nr_history = -1;
            c.future_nr = D;
            if (ct.maxCfdOn) { c.max_between = ct.maxCfdV; c.cost_max_between = ct.maxCfdW; }
            if (ct.minCfdOn) { c.min_between = ct.minCfdV; c.cost_min_between = ct.minCfdW; }
            out.push_back(c);
        }
        {  // total assignments
            Cond c(size);
            for (int i = 0; i < size; i++) c.numbering[i] = i;
            if (ct.maxAssignOn) { c.max_total = ct.maxAssignV; c.cost_max_total = ct.maxAssignW; }
            if (ct.minAssignOn) { c.min_total = ct.minAssignV; c.cost_min_total = ct.minAssignW; }
            out.push_back(c);
        }
        auto wl = weekendLayout(ct);
        int begin = wl.first, ln = wl.second;
        if (ct.identOn) {  // identical shift types during weekend
            Cond c(size);
            int b = begin + (sp.firstSaturday == 0 ? 7 : 0);
            int getal = 1;
            for (int i = 0; i < sp.numWeekends; i++) {
                for (int k = 0; k < S; k++) {
                    for (int j = 0; j < ln; j++) {
                        int day = b + i * 7 + j;
                        if (0 <= day && day < D) c.numbering[day * S + k] = getal;
                    }
                    if (getal < size) { c.min_pert[getal] = ln; c.cost_min_pert[getal] = ct.identW; }
                    getal++;
                }
                getal += ln + 1;
            }
            out.push_back(c);
        }
        if (ct.completeOn) {  // complete weekends
            Cond c(size);
            int counter = 0;
            for (int i = 0; i < sp.numWeekends; i++) {
                for (int j = 0; j < ln; j++) {
                    int day = begin + i * 7 + j;
                    if (0 <= day && day < D)
                        for (int k = 0; k < S; k++) c.numbering[day * S + k] = counter;
                    counter++;
                }
                counter += 2;
            }
            c.min_consecutive = ln;
            c.cost_min_consecutive = ct.completeW;
            out.push_back(c);
        }
        if (!sp.dayOff[e].empty()) {  // requested days off
            Cond c(size);
            int counter = 0;
            for (auto& pr : sp.dayOff[e]) {
                for (int k = 0; k < S; k++) c.numbering[pr.first * S + k] = counter;
                c.max_pert[counter] = 0;
                c.cost_max_pert[counter] = pr.second;
                counter++;
            }
            out.push_back(c);
        }
        if (!sp.shiftOff[e].empty()) {  // requested shifts off
            Cond c(size);
            int counter = 0;
            for (auto& t : sp.shiftOff[e]) {
                c.numbering[std::get<0>(t) * S + std::get<1>(t)] = counter;
                c.max_pert[counter] = 0;
                c.cost_max_pert[counter] = std::get<2>(t);
                counter++;
            }
            out.push_back(c);
        }
        {  // consecutive working weekends
            Cond c(size);
            int b = begin + (sp.firstSaturday == 0 ? 7 : 0);
            for (int i = 0; i < sp.numWeekends; i++)
                for (int j = 0; j < ln; j++) {
                    int day = b + i * 7 + j;
                    if (0 <= day && day < D)
                        for (int k = 0; k < S; k++) c.numbering[day * S + k] = i;
                }
            if (ct.minCwwOn) { c.min_consecutive = ct.minCwwV; c.cost_min_consecutive = ct.minCwwW; }
            if (ct.maxCwwOn) { c.max_consecutive = ct.maxCwwV; c.cost_max_consecutive = ct.maxCwwW; }
            out.push_back(c);
        }
        if (ct.altSkillOn) {  // alternative skill
            Cond c(size);
            int nr = 0;
            for (int pos = 0; pos < size && nr < size; pos++) {
                int si = pos % S;
                bool ok = true;
                for (auto& sk : sp.shiftSkills[si])
                    if (!sp.empSkills[e].count(sk)) { ok = false; break; }
                if (ok) continue;
                c.numbering[pos] = nr;
                c.max_pert[nr] = 0;
                c.cost_max_pert[nr] = ct.altSkillW;
                nr++;
            }
            out.push_back(c);
        }
        for (const auto& pid : ct.patternIds) {  // unwanted patterns
            const Pattern& pat = sp.patterns.at(pid);
            int plen = (int)pat.entries.size();
            std::vector<std::string> types(plen);
            for (int i = 0; i < plen; i++)
                types[i] = (pat.entries[i].first == "Any" || pat.entries[i].first == "None")
                           ? pat.entries[i].first : "S";
            bool allS = true;
            for (auto& t : types) if (t != "S") allS = false;
            if (allS && pat.entries[0].second == "Any") {
                for (int w0 = 0; w0 < plen; w0++) {
                    Cond c(size);
                    int counter = 0;
                    for (int j = 0; w0 + j * plen + plen - 1 < D; j++) {
                        int daypos = w0 + j * plen;
                        for (int i = 0; i < plen; i++) {
                            int si = sp.shiftIndex.at(pat.entries[i].first);
                            c.numbering[(daypos + i) * S + si] = counter++;
                        }
                        counter += 2;
                    }
                    c.max_consecutive = plen - 1;
                    c.cost_max_consecutive = pat.weight;
                    out.push_back(c);
                }
            } else if (types[0] == "None" && pat.entries[0].second != "Any") {
                bool restAny = true;
                for (int i = 1; i < plen; i++) if (types[i] != "Any") restAny = false;
                if (!restAny) { fprintf(stderr, "unsupported pattern %s\n", pid.c_str()); exit(3); }
                static const std::map<std::string,int> dmap = {
                    {"Monday",0},{"Tuesday",1},{"Wednesday",2},{"Thursday",3},
                    {"Friday",4},{"Saturday",5},{"Sunday",6}};
                int target = dmap.at(pat.entries[0].second);
                int firstOcc = -1;
                for (int i = 0; i < std::min(7, D); i++)
                    if (sp.weekday[i] == target) { firstOcc = i; break; }
                int numWeeks = (D + 6) / 7;
                for (int j = 0; j < numWeeks; j++) {
                    int daypos = firstOcc + j * 7;
                    if (daypos >= D) continue;
                    Cond c(size);
                    c.last_nr_history = 0;
                    for (int k = 0; k < S; k++) c.numbering[daypos * S + k] = 3;
                    for (int i = 1; i < plen; i++)
                        if (daypos + i < D)
                            for (int k = 0; k < S; k++) c.numbering[(daypos + i) * S + k] = 4;
                    c.max_between = 2;
                    c.cost_max_between = pat.weight;
                    out.push_back(c);
                }
            } else if (allS) {
                static const std::map<std::string,int> dmap = {
                    {"Monday",0},{"Tuesday",1},{"Wednesday",2},{"Thursday",3},
                    {"Friday",4},{"Saturday",5},{"Sunday",6}};
                int target = dmap.at(pat.entries[0].second);
                int firstOcc = -1;
                for (int i = 0; i < std::min(7, D); i++)
                    if (sp.weekday[i] == target) { firstOcc = i; break; }
                Cond c(size);
                int counter = 0;
                int numWeeks = (D + 6) / 7;
                for (int j = 0; j < numWeeks; j++) {
                    int daypos = firstOcc + j * 7;
                    if (daypos + plen - 1 >= D) continue;
                    for (int i = 0; i < plen; i++) {
                        int si = sp.shiftIndex.at(pat.entries[i].first);
                        c.numbering[(daypos + i) * S + si] = counter + i;
                    }
                    counter += plen + 2;
                }
                c.max_consecutive = plen - 1;
                c.cost_max_consecutive = pat.weight;
                out.push_back(c);
            } else {
                fprintf(stderr, "unsupported pattern shape %s\n", pid.c_str());
                exit(3);
            }
        }
        return out;
    }
    int runCond(const Cond& c, const std::vector<char>& worked) const {
        long pen = 0;
        int total = 0, consecutive = 1, last_nr = c.last_nr_history;
        bool event = false;
        std::vector<int> pert(c.numbering.size(), 0);
        for (size_t pos = 0; pos < worked.size(); pos++) {
            if (!worked[pos]) continue;
            int nr = c.numbering[pos];
            if (nr == UU) continue;
            event = true;
            total++;
            if (nr == last_nr + 1) {
                consecutive++;
            } else if (nr > last_nr + 1) {
                if (0 < consecutive && consecutive < c.min_consecutive && c.cost_min_consecutive > 0)
                    pen += (long)c.cost_min_consecutive * (c.min_consecutive - consecutive);
                if (consecutive > c.max_consecutive && c.cost_max_consecutive > 0)
                    pen += (long)c.cost_max_consecutive * (consecutive - c.max_consecutive);
                int g = nr - last_nr - 1;
                if (g < c.min_between && c.cost_min_between > 0)
                    pen += (long)c.cost_min_between * (c.min_between - g);
                if (g > c.max_between && c.cost_max_between > 0)
                    pen += (long)c.cost_max_between * (g - c.max_between);
                consecutive = 1;
            }
            pert[nr]++;
            last_nr = nr;
        }
        if (total > c.max_total && c.cost_max_total > 0)
            pen += (long)c.cost_max_total * (total - c.max_total);
        if (total < c.min_total && c.cost_min_total > 0)
            pen += (long)c.cost_min_total * (c.min_total - total);
        if (c.future_nr != UU && last_nr == c.future_nr - 1) consecutive++;
        if (event && consecutive > c.max_consecutive && c.cost_max_consecutive > 0)
            pen += (long)c.cost_max_consecutive * (consecutive - c.max_consecutive);
        if (last_nr != UU && consecutive < c.min_consecutive && c.cost_min_consecutive > 0)
            pen += (long)c.cost_min_consecutive * (c.min_consecutive - consecutive);
        if (last_nr != UU && c.future_nr != UU && c.cost_max_between > 0) {
            int val = c.future_nr - last_nr - 1;
            if (val > c.max_between) pen += (long)c.cost_max_between * (val - c.max_between);
        }
        if (last_nr != UU && c.future_nr != UU && c.cost_min_between > 0) {
            int val = c.future_nr - last_nr - 1;
            if (0 < val && val < c.min_between) pen += (long)c.cost_min_between * (c.min_between - val);
        }
        for (size_t t = 0; t < pert.size(); t++) {
            if (pert[t] != 0 && pert[t] > c.max_pert[t] && c.cost_max_pert[t] > 0)
                pen += (long)c.cost_max_pert[t] * (pert[t] - c.max_pert[t]);
            if (pert[t] == 0 || pert[t] >= c.min_pert[t] || c.cost_min_pert[t] <= 0) continue;
            pen += (long)c.cost_min_pert[t] * (c.min_pert[t] - pert[t]);
        }
        return (int)pen;
    }
    // penalty of one employee given roster: assign[e][day] = shift idx or -1
    int empPenalty(int e, const std::vector<std::vector<int>>& assign) const {
        std::vector<char> worked(size, 0);
        for (int d = 0; d < D; d++)
            if (assign[e][d] >= 0) worked[d * S + assign[e][d]] = 1;
        long pen = 0;
        for (const Cond& c : conds[e]) pen += runCond(c, worked);
        return (int)pen;
    }
    int totalPenalty(const std::vector<std::vector<int>>& assign) const {
        long pen = 0;
        for (size_t e = 0; e < sp.emps.size(); e++) pen += empPenalty((int)e, assign);
        return (int)pen;
    }
};

// ---------------------------------------------------------------------------
// Baseline: penalty-aware greedy construction + a short fixed-iteration
// simulated annealing. Deterministic: fixed seed and a fixed iteration
// count (the wall-clock cap is only a safety valve).
// ---------------------------------------------------------------------------
int main(int argc, char** argv) {
    std::string xml((std::istreambuf_iterator<char>(std::cin)),
                    std::istreambuf_iterator<char>());
    Instance sp = loadInstance(xml);
    Evaluator ev(sp);
    int E = (int)sp.emps.size(), D = sp.numDays, S = (int)sp.shifts.size();

    double pool = 60.0;
    const char* tp = getenv("NURSE_INSTANCE_SECONDS");
    if (!tp) tp = getenv("NURSE_TIME_POOL");
    if (tp) pool = atof(tp);
    // safety cap: the pool covers many instances; spend little here. Sized
    // well above the natural completion time of the fixed cycle program, so
    // it only bites on pathologically slow machines.
    double cap = std::min(45.0, pool * 0.10 + 1.0);
    auto t0 = std::chrono::steady_clock::now();
    auto elapsed = [&]() {
        return std::chrono::duration<double>(std::chrono::steady_clock::now() - t0).count();
    };

    std::mt19937 rng(12345);

    // greedy: fill each demand slot with the nurse whose incremental penalty
    // is smallest (ties: fewer assignments, then lower index)
    auto greedy = [&](std::vector<std::vector<int>>& assign) {
        assign.assign(E, std::vector<int>(D, -1));
        std::vector<int> load(E, 0);
        for (int d = 0; d < D; d++) {
            for (int s = 0; s < S; s++) {
                auto it = sp.cover.find({d, s});
                if (it == sp.cover.end()) continue;
                int need = it->second;
                for (int r = 0; r < need; r++) {
                    int best = -1;
                    long bestCost = -1;
                    for (int e = 0; e < E; e++) {
                        if (assign[e][d] != -1) continue;
                        assign[e][d] = s;
                        long c = ev.empPenalty(e, assign);
                        assign[e][d] = -1;
                        if (best == -1 || c < bestCost ||
                            (c == bestCost && load[e] < load[best])) {
                            best = e;
                            bestCost = c;
                        }
                    }
                    if (best == -1) break;  // cannot happen in these instances
                    assign[best][d] = s;
                    load[best]++;
                }
            }
        }
    };

    std::vector<std::vector<int>> assign, bestAssign;
    greedy(assign);
    std::vector<int> empPen(E, 0);
    int curPen = 0;
    for (int e = 0; e < E; e++) { empPen[e] = ev.empPenalty(e, assign); curPen += empPen[e]; }
    bestAssign = assign;
    int bestPen = curPen;

    // Simulated annealing over four coverage-preserving move types, with a
    // FIXED iteration count (per instance size) so the result is
    // deterministic and machine-independent; the wall-clock cap is only a
    // safety valve for pathologically slow machines and must not trigger in
    // practice (see SELF-CHECK.md).
    long ITERS = (E <= 15) ? 6000 : (E <= 35) ? 40000 : 80000;
    const char* itEnv = getenv("NURSE_ITERS");
    if (itEnv) ITERS = atol(itEnv);  // tuning hook (not used at judging)
    const double T0 = 8.0, Tend = 0.05;
    std::vector<std::pair<int,int>> weekendPairs;
    for (int i = 0; i + 1 < D; i++)
        if (sp.weekday[i] == 5 && sp.weekday[i + 1] == 6) weekendPairs.push_back({i, i + 1});
    auto rnd = [&]() { return rng() / (double)rng.max(); };
    for (long it = 0; it < ITERS; it++) {
        double T = T0 * pow(Tend / T0, (double)it / (double)ITERS);
        int mt = rng() % 100;
        if (mt < 40) {
            // transfer (e1,d,s) -> (e2,d,s), e2 free on d
            int d = rng() % D;
            std::vector<int> workers, idle;
            for (int e = 0; e < E; e++)
                (assign[e][d] >= 0 ? workers : idle).push_back(e);
            if (workers.empty() || idle.empty()) continue;
            int e1 = workers[rng() % workers.size()];
            int e2 = idle[rng() % idle.size()];
            int s1 = assign[e1][d];
            int before = empPen[e1] + empPen[e2];
            assign[e1][d] = -1; assign[e2][d] = s1;
            int p1 = ev.empPenalty(e1, assign), p2 = ev.empPenalty(e2, assign);
            int delta = p1 + p2 - before;
            if (delta <= 0 || rnd() < exp(-delta / T)) {
                empPen[e1] = p1; empPen[e2] = p2; curPen += delta;
            } else { assign[e1][d] = s1; assign[e2][d] = -1; }
        } else if (mt < 70) {
            // swap shifts of two workers on the same day
            int d = rng() % D;
            std::vector<int> workers;
            for (int e = 0; e < E; e++)
                if (assign[e][d] >= 0) workers.push_back(e);
            if (workers.size() < 2) continue;
            int e1 = workers[rng() % workers.size()];
            int e2 = workers[rng() % workers.size()];
            if (e1 == e2) continue;
            int s1 = assign[e1][d], s2 = assign[e2][d];
            if (s1 == s2) continue;
            int before = empPen[e1] + empPen[e2];
            assign[e1][d] = s2; assign[e2][d] = s1;
            int p1 = ev.empPenalty(e1, assign), p2 = ev.empPenalty(e2, assign);
            int delta = p1 + p2 - before;
            if (delta <= 0 || rnd() < exp(-delta / T)) {
                empPen[e1] = p1; empPen[e2] = p2; curPen += delta;
            } else { assign[e1][d] = s1; assign[e2][d] = s2; }
        } else if (mt < 82 && !weekendPairs.empty()) {
            // swap whole weekends between two nurses
            auto wp = weekendPairs[rng() % weekendPairs.size()];
            int e1 = rng() % E, e2 = rng() % E;
            if (e1 == e2) continue;
            int a1 = assign[e1][wp.first], b1 = assign[e1][wp.second];
            int a2 = assign[e2][wp.first], b2 = assign[e2][wp.second];
            if (a1 == a2 && b1 == b2) continue;
            int before = empPen[e1] + empPen[e2];
            assign[e1][wp.first] = a2; assign[e1][wp.second] = b2;
            assign[e2][wp.first] = a1; assign[e2][wp.second] = b1;
            int p1 = ev.empPenalty(e1, assign), p2 = ev.empPenalty(e2, assign);
            int delta = p1 + p2 - before;
            if (delta <= 0 || rnd() < exp(-delta / T)) {
                empPen[e1] = p1; empPen[e2] = p2; curPen += delta;
            } else {
                assign[e1][wp.first] = a1; assign[e1][wp.second] = b1;
                assign[e2][wp.first] = a2; assign[e2][wp.second] = b2;
            }
        } else {
            // segment transfer: move a sub-segment of e1's work run to e2
            int e1 = rng() % E;
            int d0 = rng() % D;
            if (assign[e1][d0] < 0) continue;
            int lo = d0, hi = d0;
            while (lo > 0 && assign[e1][lo - 1] >= 0) lo--;
            while (hi + 1 < D && assign[e1][hi + 1] >= 0) hi++;
            int a = lo + rng() % (hi - lo + 1), b = lo + rng() % (hi - lo + 1);
            if (a > b) std::swap(a, b);
            int e2 = rng() % E;
            if (e2 == e1) continue;
            bool free = true;
            for (int dd = a; dd <= b; dd++)
                if (assign[e2][dd] >= 0) { free = false; break; }
            if (!free) continue;
            int before = empPen[e1] + empPen[e2];
            std::vector<int> saved;
            for (int dd = a; dd <= b; dd++) {
                saved.push_back(assign[e1][dd]);
                assign[e2][dd] = assign[e1][dd];
                assign[e1][dd] = -1;
            }
            int p1 = ev.empPenalty(e1, assign), p2 = ev.empPenalty(e2, assign);
            int delta = p1 + p2 - before;
            if (delta <= 0 || rnd() < exp(-delta / T)) {
                empPen[e1] = p1; empPen[e2] = p2; curPen += delta;
            } else {
                for (size_t i2 = 0; i2 < saved.size(); i2++) {
                    assign[e1][a + (int)i2] = saved[i2];
                    assign[e2][a + (int)i2] = -1;
                }
            }
        }
        if (curPen < bestPen) { bestPen = curPen; bestAssign = assign; }
        if ((it & 8191) == 0 && elapsed() > cap) break;  // safety valve only
    }

    // emit the roster
    printf("<?xml version=\"1.0\" encoding=\"utf-8\"?>\n<Solution>\n");
    printf("  <SchedulingPeriodID>%s</SchedulingPeriodID>\n", sp.id.c_str());
    printf("  <Competitor>baseline</Competitor>\n");
    printf("  <SoftConstraintsPenalty>%d</SoftConstraintsPenalty>\n", bestPen);
    for (int e = 0; e < E; e++)
        for (int d = 0; d < D; d++)
            if (bestAssign[e][d] >= 0)
                printf("  <Assignment><Date>%s</Date><Employee>%s</Employee><ShiftType>%s</ShiftType></Assignment>\n",
                       sp.dateStr[d].c_str(), sp.emps[e].c_str(), sp.shifts[bestAssign[e][d]].c_str());
    printf("</Solution>\n");
    return 0;
}
