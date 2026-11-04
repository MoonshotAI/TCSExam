#![allow(non_snake_case, unused_macros)]

use anyhow::{anyhow, bail, ensure, Result};
use itertools::Itertools;
use proconio::input;
use rand::prelude::*;
use std::{collections::HashSet, i64, ops::RangeBounds};
use svg::node::element::{Circle, Group, Line, Rectangle, Style, Title};

pub trait SetMinMax {
    fn setmin(&mut self, v: Self) -> bool;
    fn setmax(&mut self, v: Self) -> bool;
}
impl<T> SetMinMax for T
where
    T: PartialOrd,
{
    fn setmin(&mut self, v: T) -> bool {
        *self > v && {
            *self = v;
            true
        }
    }
    fn setmax(&mut self, v: T) -> bool {
        *self < v && {
            *self = v;
            true
        }
    }
}

#[macro_export]
macro_rules! mat {
	($($e:expr),*) => { Vec::from(vec![$($e),*]) };
	($($e:expr,)*) => { Vec::from(vec![$($e),*]) };
	($e:expr; $d:expr) => { Vec::from(vec![$e; $d]) };
	($e:expr; $d:expr $(; $ds:expr)+) => { Vec::from(vec![mat![$e $(; $ds)*]; $d]) };
}

const MAX_XY: i64 = 1000;
const RADIUS: i64 = MAX_XY / 2;
const MIN_D: i64 = 15;
const MAX_A: i64 = 100;

#[derive(Clone, Debug)]
pub struct Input {
    N: usize,
    M: usize,
    H: i64,
    A: Vec<i64>,
    edges: Vec<(usize, usize)>,
    points: Vec<(i64, i64)>,
}

impl Input {
    fn new(
        N: usize,
        H: i64,
        A: Vec<i64>,
        edges: Vec<(usize, usize)>,
        points: Vec<(i64, i64)>,
    ) -> Self {
        // for binary search
        let mut edges = edges
            .into_iter()
            .map(|(u, v)| (u.min(v), u.max(v)))
            .collect_vec();
        edges.sort_unstable();

        Self {
            N,
            M: edges.len(),
            H,
            A,
            edges,
            points,
        }
    }

    fn contains_edge(&self, u: usize, v: usize) -> bool {
        self.edges.binary_search(&(u.min(v), u.max(v))).is_ok()
    }
}

impl std::fmt::Display for Input {
    fn fmt(&self, f: &mut std::fmt::Formatter<'_>) -> std::fmt::Result {
        writeln!(f, "{} {} {}", self.N, self.M, self.H)?;
        writeln!(f, "{}", self.A.iter().join(" "))?;

        for &(u, v) in &self.edges {
            writeln!(f, "{} {}", u, v)?;
        }

        for &(x, y) in &self.points {
            writeln!(f, "{} {}", x, y)?;
        }

        Ok(())
    }
}

pub fn parse_input(f: &str) -> Input {
    let f = proconio::source::once::OnceSource::from(f);
    input! {
        from f,
        N: usize,
        M: usize,
        H: i64,
        A: [i64; N],
        edges: [(usize, usize); M],
        points: [(i64, i64); N],
    }

    Input::new(N, H, A, edges, points)
}

pub fn read<T: Copy + PartialOrd + std::fmt::Display + std::str::FromStr, R: RangeBounds<T>>(
    token: Option<&str>,
    range: R,
) -> Result<T> {
    if let Some(v) = token {
        if let Ok(v) = v.parse::<T>() {
            ensure!(range.contains(&v), "Out of range: {}", v);
            Ok(v)
        } else {
            bail!("Parse error: {}", v)
        }
    } else {
        bail!("Unexpected EOF")
    }
}

pub struct Output {
    pub out: Vec<OutputSingle>,
}

impl Output {
    pub fn new(out: Vec<OutputSingle>) -> Self {
        Self { out }
    }
}

#[derive(Debug, Clone)]
pub struct OutputSingle {
    pub parents: Vec<i32>,
}

impl OutputSingle {
    pub fn new(parents: Vec<i32>) -> Self {
        Self { parents }
    }

    pub fn to_tree_nodes(&self, input: &Input) -> Result<Vec<TreeNode>> {
        let mut nodes = TreeNode::gen_default(input);
        let mut edges = vec![vec![]; input.N];
        let mut indegrees = vec![0; input.N];

        for (v, &p) in self.parents.iter().enumerate() {
            if p == -1 {
                continue;
            }

            let p = p as usize;
            nodes[v].parent = Some(p);

            ensure!(
                input.contains_edge(v.min(p), v.max(p)),
                "Edge ({}, {}) is not included in the original graph.",
                v,
                p
            );

            indegrees[v] += 1;
            edges[p].push(v);
        }

        for v in 0..input.N {
            if indegrees[v] == 0 {
                Self::dfs(v, 0, v, &mut nodes, &edges);
            }
        }

        Ok(nodes)
    }

    fn dfs(v: usize, h: i64, root: usize, nodes: &mut [TreeNode], edges: &[Vec<usize>]) {
        nodes[v].h = Some(h);
        nodes[v].root = Some(root);

        for &child in edges[v].iter() {
            Self::dfs(child, h + 1, root, nodes, edges);
        }
    }
}

#[derive(Debug, Clone, Copy)]
pub struct TreeNode {
    pub id: usize,
    pub parent: Option<usize>,
    pub root: Option<usize>,
    pub h: Option<i64>,
}

impl TreeNode {
    pub fn new(id: usize, parent: Option<usize>, root: Option<usize>, h: Option<i64>) -> Self {
        Self {
            id,
            parent,
            root,
            h,
        }
    }

    fn score(&self, input: &Input) -> i64 {
        let h = self.h.unwrap_or(i64::MAX);

        if h <= input.H {
            input.A[self.id] * (h + 1)
        } else {
            0
        }
    }

    pub fn gen_default(input: &Input) -> Vec<Self> {
        (0..input.N)
            .map(|i| Self::new(i, None, None, None))
            .collect()
    }
}

pub fn parse_output(input: &Input, f: &str) -> Result<Output> {
    let mut f = f.split_whitespace().peekable();
    let mut out = vec![];

    while f.peek().is_some() {
        let mut parents = vec![];

        for _ in 0..input.N {
            let parent = read(f.next(), -1..input.N as i32)?;
            parents.push(parent);
        }

        out.push(OutputSingle::new(parents));
    }

    Ok(Output::new(out))
}

pub fn gen(seed: u64) -> Input {
    const N: usize = 1000;
    const H: i64 = 10;
    let mut rng = rand_chacha::ChaCha20Rng::seed_from_u64(seed);

    // gen points
    let mut points = vec![];

    for _ in 0..N {
        loop {
            let x = rng.gen_range(0..=MAX_XY);
            let y = rng.gen_range(0..=MAX_XY);

            if dist_sq((x, y), (RADIUS, RADIUS)) <= RADIUS * RADIUS
                && points.iter().all(|&p| dist_sq((x, y), p) > MIN_D * MIN_D)
            {
                points.push((x, y));
                break;
            }
        }
    }

    // gen edges
    let ps_f64 = points
        .iter()
        .map(|&(x, y)| delaunator::Point {
            x: x as f64,
            y: y as f64,
        })
        .collect_vec();
    let triangles = delaunator::triangulate(&ps_f64).triangles;
    assert_eq!(triangles.len() % 3, 0);

    let mut edges = vec![];

    for triangle in triangles.chunks(3) {
        for i in 0..3 {
            let u = triangle[i];
            let v = triangle[(i + 1) % 3];
            assert_ne!(u, v);
            edges.push((u.min(v), u.max(v)));
        }
    }

    edges.sort_unstable();
    edges.dedup();

    // gen A
    let A = (0..N).map(|_| rng.gen_range(1..=MAX_A)).collect_vec();

    Input::new(N, H, A, edges, points)
}

fn dist_sq((x1, y1): (i64, i64), (x2, y2): (i64, i64)) -> i64 {
    let dx = x1 - x2;
    let dy = y1 - y2;
    dx * dx + dy * dy
}

pub fn compute_score(input: &Input, out: &Output) -> Result<i64> {
    match out.out.last() {
        Some(out) => out
            .to_tree_nodes(input)
            .and_then(|nodes| compute_score_details(input, &nodes)),
        None => Err(anyhow!("empty output")),
    }
}

pub fn compute_score_details(input: &Input, nodes: &[TreeNode]) -> Result<i64> {
    let mut score = 1;

    for v in 0..input.N {
        ensure!(
            nodes[v].root.is_some(),
            "The connected component that contains vertex {} is not a rooted tree.",
            v
        );
    }

    for v in 0..input.N {
        let h = nodes[v].h.unwrap();
        ensure!(h <= input.H as i64, "Vertex {} is too high (h = {}).", v, h);
    }

    for node in nodes.iter() {
        score += node.score(input);
    }

    Ok(score)
}

/// 0 <= val <= 1
pub fn color(mut val: f64) -> String {
    val.setmin(1.0);
    val.setmax(0.0);
    let (r, g, b) = if val < 0.5 {
        let x = val * 2.0;
        (
            30. * (1.0 - x) + 144. * x,
            144. * (1.0 - x) + 255. * x,
            255. * (1.0 - x) + 30. * x,
        )
    } else {
        let x = val * 2.0 - 1.0;
        (
            144. * (1.0 - x) + 255. * x,
            255. * (1.0 - x) + 30. * x,
            30. * (1.0 - x) + 70. * x,
        )
    };
    format!(
        "#{:02x}{:02x}{:02x}",
        r.round() as i32,
        g.round() as i32,
        b.round() as i32
    )
}

pub fn rect(x: i64, y: i64, w: i64, h: i64, fill: &str) -> Rectangle {
    Rectangle::new()
        .set("x", x)
        .set("y", y)
        .set("width", w)
        .set("height", h)
        .set("fill", fill)
}

pub fn group(title: String) -> Group {
    Group::new().add(Title::new(title))
}

pub fn vis_default(input: &Input, out: &Output) -> (i64, String, String) {
    match out
        .out
        .last()
        .ok_or_else(|| anyhow!("empty output"))
        .and_then(|out| out.to_tree_nodes(input))
    {
        Ok(nodes) => {
            let VisResult { score, err, svg } = vis(input, &nodes, ColorOption::A);
            (score, err, svg)
        }
        Err(err) => {
            let VisResult { score, svg, .. } =
                vis(input, &TreeNode::gen_default(input), ColorOption::A);
            (score, err.to_string(), svg)
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum ColorOption {
    A,
    H,
    Score,
}

pub struct VisResult {
    pub score: i64,
    pub err: String,
    pub svg: String,
}

pub fn vis(input: &Input, tree_nodes: &[TreeNode], color_option: ColorOption) -> VisResult {
    const W: i64 = 800;
    const H: i64 = 800;
    const PADDING: i64 = 10;

    let (score, err) = match compute_score_details(input, &tree_nodes) {
        Ok(score) => (score, "".to_string()),
        Err(err) => (0, err.to_string()),
    };

    let mut doc = svg::Document::new()
        .set("id", "vis")
        .set(
            "viewBox",
            (
                -PADDING,
                -PADDING,
                MAX_XY + 2 * PADDING,
                MAX_XY + 2 * PADDING,
            ),
        )
        .set("width", W)
        .set("height", H)
        .set("style", "background-color:white");
    doc = doc.add(Style::new(format!(
        "text {{text-anchor: middle;dominant-baseline: central;}}"
    )));

    let mut used_edges = HashSet::new();

    for (i, node) in tree_nodes.iter().enumerate() {
        let Some(parent) = node.parent else {
            continue;
        };

        used_edges.insert((i.min(parent), i.max(parent)));
    }

    // draw edges
    let mut edges = input.edges.clone();
    edges.sort_by_key(|e| used_edges.contains(e));

    for &(u, v) in edges.iter() {
        let stroke = if used_edges.contains(&(u, v)) {
            "dimgray"
        } else {
            "lightgray"
        };
        let stroke_width = if used_edges.contains(&(u, v)) { 2 } else { 1 };
        let line = Line::new()
            .set("x1", input.points[u].0)
            .set("y1", input.points[u].1)
            .set("x2", input.points[v].0)
            .set("y2", input.points[v].1)
            .set("stroke", stroke)
            .set("stroke-width", stroke_width);
        doc = doc.add(line);
    }

    for i in 0..input.N {
        let h = to_string_or_none(tree_nodes[i].h);
        let parent = to_string_or_none(tree_nodes[i].parent);
        let root = to_string_or_none(tree_nodes[i].root);
        let is_root = tree_nodes[i].root == Some(i);

        let node_score = tree_nodes[i].score(input);
        let score_txt = if node_score == 0 {
            "0".to_string()
        } else {
            format!(
                "({} + 1) * {} = {}",
                tree_nodes[i].h.unwrap(),
                input.A[i],
                node_score
            )
        };

        let title = format!(
            "vertex {}\n(x, y): ({}, {})\nA[i]: {}\nparent: {}\nroot: {}\nis_root: {}\nh: {}\nscore: {}",
            i, input.points[i].0, input.points[i].1, input.A[i], parent, root, is_root, h, score_txt
        );

        let stroke_width = if is_root { 4 } else { 2 };
        let stroke = if is_root { "#222222" } else { "dimgray" };
        let color = match color_option {
            ColorOption::A => color(input.A[i] as f64 / MAX_A as f64),
            ColorOption::H => color(tree_nodes[i].h.unwrap_or(0) as f64 / input.H as f64),
            ColorOption::Score => {
                color((node_score as f64 / ((input.H + 1) * MAX_A) as f64).sqrt())
            }
        };

        let mut circle = Circle::new()
            .set("cx", input.points[i].0)
            .set("cy", input.points[i].1)
            .set("r", 5)
            .set("fill", color)
            .set("stroke", stroke)
            .set("stroke-width", stroke_width);

        if let Some(root) = tree_nodes[i].root {
            circle = circle
                .set("class", format!("tree{}", root))
                .set("onmouseover", format!("focus_tree({})", root))
                .set("onmouseleave", format!("unfocus_tree({})", root));
        }

        doc = doc.add(group(title).add(circle));
    }

    VisResult {
        score,
        err,
        svg: doc.to_string(),
    }
}

fn to_string_or_none<T: std::fmt::Display>(x: Option<T>) -> String {
    match x {
        Some(x) => x.to_string(),
        None => "None".to_string(),
    }
}
