import katex from "katex";
import "katex/dist/katex.min.css";

export function renderEquation(element) {
  katex.render(element.dataset.math, element, {
    throwOnError: true,
    displayMode: element.classList.contains("formula"),
    strict: "error",
    trust: false,
    output: "htmlAndMathml",
  });
}
