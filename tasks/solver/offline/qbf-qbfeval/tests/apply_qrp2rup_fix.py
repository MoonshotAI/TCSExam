import hashlib,sys
from pathlib import Path
p=Path(sys.argv[1]);b=p.read_bytes()
assert hashlib.sha256(b).hexdigest()=="a8d155e3f9a1b238043e2ab131b86937d3be4c05ecf12d9b7cb1e80437d8e908"
s=b.decode()
changes=[("constraint_type.resize(empty_constraint_id+1, 0);","constraint_type.resize(empty_constraint_id+3, 0);"),("spare_QRP_IDs[1] = empty_constraint_id + 2;","spare_QRP_IDs[1] = empty_constraint_id + 2;\n\tconstraint_type[spare_QRP_IDs[0]] = primary_type;\n\tconstraint_type[spare_QRP_IDs[1]] = primary_type;"),("temporary_resolvent = spare_QRP_IDs[spare_QRP_ID_idx];","temporary_resolvent = spare_QRP_IDs[spare_QRP_ID_idx];\n\t\t\t\t\tconstraint_type[temporary_resolvent] = constraint_type[parents_right[i]];"),("QRP_ClauseID reduct_id = spare_QRP_IDs[0];","QRP_ClauseID reduct_id = spare_QRP_IDs[0];\n\t\tconstraint_type[reduct_id] = constraint_type[current_id];")]
for a,c in changes:
 assert s.count(a)==1,a
 s=s.replace(a,c)
assert hashlib.sha256(s.encode()).hexdigest()=="f20dab525ac27d09c737b6f2ef8565d4e6776162c3133fc4b8dd96d90c119faf"
p.write_text(s)
