const pptxgen = require("pptxgenjs");
const React = require("react");
const ReactDOMServer = require("react-dom/server");
const sharp = require("sharp");
const fa = require("react-icons/fa6");
const fs = require("fs");
const path = require("path");
const { applyTheme } = require(process.argv[3]);

const OUT = process.argv[2];
const DATA = JSON.parse(fs.readFileSync(path.join(__dirname, "data.json"), "utf8"));

// Model colours match the report charts
const HEX = {
  navy: "1B2A41", ink: "1F2328", grey: "6B6A66", light: "EEF1F5", line: "D9DCE1", tint: "2A3B55",
  lgb: "2A78D6", ens: "0F5C73", chronos: "EB6834", arima: "1BAF7A", ets: "D55181", claude: "4A3AA7", naive: "9A9993", amber: "F2B33D",
};
const THEME = {
  name: "Group 3 Forecasting", headFontFace: "Cambria", bodyFontFace: "Calibri",
  colors: { dk1: HEX.ink, lt1: "FFFFFF", dk2: HEX.navy, lt2: HEX.light, accent1: HEX.lgb, accent2: HEX.chronos,
            accent3: HEX.arima, accent4: HEX.claude, accent5: HEX.ets, accent6: HEX.amber, hlink: HEX.lgb, folHlink: HEX.claude },
};
const famColor = name => {
  if (name.startsWith("Claude")) return HEX.claude;
  if (name.startsWith("LightGBM")) return HEX.lgb;
  if (name.startsWith("Ensemble")) return HEX.ens;
  if (name.startsWith("AutoETS")) return HEX.ets;
  if (name.startsWith("AutoARIMA")) return HEX.arima;
  if (name.startsWith("Chronos")) return HEX.chronos;
  return HEX.naive;
};
const pale = { [HEX.lgb]: "AFCDF2", [HEX.ets]: "EDB9CC", [HEX.arima]: "A6DCC6", [HEX.chronos]: "F6BFA6", [HEX.naive]: "D3D2CE", [HEX.ens]: "9FC0CB", [HEX.claude]: "B8B1E3" };

async function icon(Comp, color = "FFFFFF") {
  const svg = ReactDOMServer.renderToStaticMarkup(React.createElement(Comp, { color: "#" + color, size: 256 }));
  return "image/png;base64," + (await sharp(Buffer.from(svg)).png().toBuffer()).toString("base64");
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_WIDE";
  pres.title = "Can AI Foundation Models Beat Traditional Statistical Models?";
  pres.author = "Group 3";
  pres.theme = { headFontFace: THEME.headFontFace, bodyFontFace: THEME.bodyFontFace };
  const C = pres.SchemeColor;

  pres.defineSlideMaster({
    title: "Title Dark", background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.7, y: 0.6, w: 11.9, h: 1.2, fontSize: 44, bold: true,
          color: C.background1, valign: "bottom", align: "left" }, text: "" } },
      { placeholder: { options: { name: "body", type: "body", x: 0.7, y: 1.85, w: 11.9, h: 0.6, fontSize: 20,
          color: C.background2, valign: "top", align: "left" }, text: "" } },
    ],
  });
  pres.defineSlideMaster({
    title: "Content", background: { color: C.background1 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontSize: 34, bold: true,
          color: C.text2, valign: "middle", align: "left" }, text: "" } },
      { text: { text: "Group 3 · Time Series Analysis and Forecasting · UCLA Anderson",
                options: { x: 0.6, y: 7.0, w: 8, h: 0.3, fontSize: 10, color: C.text2, margin: 0 } } },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.text2, align: "right" },
  });
  pres.defineSlideMaster({
    title: "Closing Dark", background: { color: C.text2 },
    objects: [
      { placeholder: { options: { name: "title", type: "title", x: 0.6, y: 0.35, w: 12.1, h: 0.95, fontSize: 34, bold: true,
          color: C.background1, valign: "middle", align: "left" }, text: "" } },
    ],
    slideNumber: { x: 12.2, y: 7.0, w: 0.6, h: 0.3, fontSize: 10, color: C.background2, align: "right" },
  });

  const I = {};
  for (const [k, comp] of Object.entries({ arima: fa.FaChartLine, ets: fa.FaWaveSquare, lgb: fa.FaTree, chronos: fa.FaHourglassHalf,
      claude: fa.FaBrain, naive: fa.FaRotateLeft, history: fa.FaClockRotateLeft, forecast: fa.FaChartLine, order: fa.FaCartShopping,
      shelf: fa.FaStore, warn: fa.FaTriangleExclamation, blind: fa.FaEyeSlash, shuffle: fa.FaShuffle, coins: fa.FaCoins,
      code: fa.FaCode, play: fa.FaPlay, sliders: fa.FaSliders, check: fa.FaClipboardCheck, layers: fa.FaLayerGroup, clock: fa.FaStopwatch })) {
    I[k] = await icon(comp);
  }
  const badge = (s, img, color, x, y, d, name) => {
    s.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color }, line: { color, width: 0 }, objectName: name + " circle" });
    s.addImage({ data: img, x: x + d * 0.24, y: y + d * 0.24, w: d * 0.52, h: d * 0.52, objectName: name + " icon" });
  };
  const text = (s, t, o) => s.addText(t, { isTextBox: true, margin: 0, ...o });
  const card = (s, x, y, w, h, name, fill = C.background2) => s.addShape(pres.shapes.ROUNDED_RECTANGLE,
    { x, y, w, h, rectRadius: 0.12, fill: { color: fill }, line: { color: fill }, objectName: name });
  const chartText = { catAxisLabelFontFace: "+mn-lt", valAxisLabelFontFace: "+mn-lt", dataLabelFontFace: "+mn-lt",
    titleFontFace: "+mn-lt", legendFontFace: "+mn-lt", catAxisLabelColor: HEX.grey, valAxisLabelColor: HEX.grey,
    catAxisLabelFontSize: 12, valAxisLabelFontSize: 11, dataLabelFontSize: 12, dataLabelColor: HEX.ink,
    valGridLine: { color: HEX.line, size: 0.5 }, catGridLine: { style: "none" }, titleColor: HEX.ink, titleFontSize: 14 };
  // One series per bar colour, zeros hidden, so each bar keeps its model's colour
  const colouredBars = (rows, colorOf) => {
    const colors = [...new Set(rows.map(r => colorOf(r)))];
    return { colors, series: colors.map(c => ({ name: c, labels: rows.map(r => r[0]), values: rows.map(r => (colorOf(r) === c ? r[1] : 0)) })) };
  };
  const hbar = (s, rows, colorOf, o) => {
    const { colors, series } = colouredBars(rows, colorOf);
    s.addChart(pres.charts.BAR, series, { ...chartText, barDir: "bar", barGrouping: "stacked", chartColors: colors,
      catAxisOrientation: "maxMin", showValue: true, dataLabelPosition: "inEnd", dataLabelFormatCode: "0.000;;;",
      dataLabelColor: "FFFFFF", valAxisMinVal: 0, valAxisMaxVal: 1, valAxisLabelFormatCode: "0.0", showLegend: false, ...o });
  };

  // =============== Speaker 1: question, data and validation
  pres.addSection({ title: "Question and data" });
  let s = pres.addSlide({ masterName: "Title Dark", sectionTitle: "Question and data" });
  s.addText("Can AI Foundation Models Beat Traditional Statistical Models?", { placeholder: "title" });
  s.addText("Retail forecasting has to balance accuracy, efficiency and business value", { placeholder: "body" });
  [["Can pre-trained AI forecast as well as traditional methods, and faster?", HEX.claude],
   ["Does a better forecast mean a better replenishment decision?", HEX.amber]].forEach(([q, col], i) => {
    const x = 0.7 + i * 6.05;
    card(s, x, 2.75, 5.85, 1.35, "question " + (i + 1), HEX.tint);
    text(s, String(i + 1), { x: x + 0.3, y: 2.75, w: 0.6, h: 1.35, fontSize: 40, bold: true, color: col, fontFace: THEME.headFontFace, valign: "middle" });
    text(s, q, { x: x + 1.0, y: 2.75, w: 4.6, h: 1.35, fontSize: 18, color: C.background1, valign: "middle" });
  });
  [["Sales history", I.history], ["Forecast", I.forecast], ["Order", I.order], ["Shelf", I.shelf]].forEach(([lab, img], i) => {
    const x = 1.2 + i * 3.0;
    badge(s, img, i === 1 ? HEX.lgb : i === 2 ? HEX.amber : "3A4D6B", x, 4.55, 0.85, lab);
    text(s, lab, { x: x - 0.5, y: 5.5, w: 1.85, h: 0.4, fontSize: 15, color: C.background2, align: "center" });
    if (i < 3) text(s, "→", { x: x + 1.3, y: 4.55, w: 1.2, h: 0.85, fontSize: 30, color: HEX.naive, align: "center", valign: "middle" });
  });
  text(s, "Group 3: Charlotte Zhu, Shihan Wang, Jing Chang, Rachel Liu · Time Series Analysis and Forecasting · UCLA Anderson",
       { x: 0.7, y: 6.6, w: 11.9, h: 0.4, fontSize: 13, color: C.background2 });
  s.addNotes("SPEAKER 1 (0:45)\n\nGood afternoon, we're Group 3. A retail forecast has three jobs: be accurate, be cheap and fast enough to run every day for thousands of products, and support good stocking decisions. LightGBM, a machine-learning method, dominates this kind of retail data and has become the industry default. Since then, AI foundation models, pre-trained on huge datasets, can forecast a product they have never seen, with no training at all. So we ask: can these AI models beat traditional statistical and machine-learning methods, on accuracy and on efficiency?\n\nTRANSITION: Here is our data and how we tested.");

  s = pres.addSlide({ masterName: "Content", sectionTitle: "Question and data" });
  s.addText("5,748 daily series, one 28-day test window", { placeholder: "title" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 0.6, y: 1.45, w: 10.2, h: 0.75, rectRadius: 0.08, fill: { color: HEX.navy }, line: { color: HEX.navy }, objectName: "train bar" });
  text(s, "Training: Jan 29, 2011 – May 22, 2016 (1,941 days) · models fitted and tuned here",
       { x: 0.85, y: 1.45, w: 9.8, h: 0.75, fontSize: 15, bold: true, color: "FFFFFF", valign: "middle" });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 10.9, y: 1.45, w: 1.8, h: 0.75, rectRadius: 0.08, fill: { color: HEX.amber }, line: { color: HEX.amber }, objectName: "test bar" });
  text(s, "Test: 28 days", { x: 10.9, y: 1.45, w: 1.8, h: 0.75, fontSize: 15, bold: true, color: HEX.ink, align: "center", valign: "middle" });
  text(s, "May 23 – Jun 19, 2016, never seen by any model. LightGBM tuning used only the last 28 training days.",
       { x: 0.6, y: 2.3, w: 12.1, h: 0.35, fontSize: 13, color: HEX.grey });
  s.addChart(pres.charts.LINE, [{ name: "Weekly units", labels: DATA.weekly.labels, values: DATA.weekly.values }], {
    x: 0.6, y: 2.85, w: 7.4, h: 3.9, ...chartText, chartColors: [HEX.navy], lineSize: 1.5, lineDataSymbol: "none",
    showLegend: false, showTitle: true, title: "Weekly food units sold, 4 California stores", valAxisLabelFormatCode: "#,##0",
    catAxisLabelFrequency: 52, catAxisLabelRotate: 0, catAxisMajorTickMark: "none", objectName: "weekly sales chart",
  });
  [["4 stores × 1,437 items", "California, food category = 5,748 item × store series"],
   ["WRMSSE", "The official M5 score: scaled, sales-weighted error; below 1 beats naive"],
   ["One test window", "All results come from a single 28 days; rankings could shift"]].forEach(([h, b], i) => {
    const y = 2.95 + i * 1.3;
    card(s, 8.4, y, 4.3, 1.15, "data card " + i);
    text(s, h, { x: 8.65, y: y + 0.1, w: 3.9, h: 0.45, fontSize: 18, bold: true, color: i === 2 ? HEX.chronos : C.text2, fontFace: THEME.headFontFace });
    text(s, b, { x: 8.65, y: y + 0.55, w: 3.9, h: 0.55, fontSize: 13, color: C.text1, valign: "top" });
  });
  s.addNotes("SPEAKER 1 (1:20)\n\nWe used Walmart's M5 data: all 1,437 food items in four California stores, so 5,748 daily series, each one item in one store, from 2011 to 2016.\n\nEvery model trains on data up to May 22, 2016, and forecasts the next 28 days, the official M5 test window, which no model sees. The one model we tuned, LightGBM, was tuned only on the last 28 training days.\n\nThree features make this data hard. Sales follow a weekly rhythm: weekends sell about 20% above an average day. Food-stamp payment days add about 10%. And demand is sparse: the typical item sells nothing on half of all days.\n\nWe score accuracy with WRMSSE, the official M5 metric: it scales each product's error by how hard it is to forecast and weights it by dollar sales. Lower is better, and below one beats a naive forecast. One caveat up front: this is a single 28-day window.\n\nTRANSITION: Speaker 2 will introduce the models.");

  // =============== Speaker 2: statistics, ML and time series foundation models
  pres.addSection({ title: "Models and results" });
  s = pres.addSlide({ masterName: "Content", sectionTitle: "Models and results" });
  s.addText("Five models plus a simple average", { placeholder: "title" });
  const hdr = ["Model", "Family", "How it is fitted", "What it sees"].map(t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.navy } } }));
  const rowsM = [
    ["AutoETS", HEX.ets, "Statistics", "One model per series (exponential smoothing)", "Own history"],
    ["AutoARIMA", HEX.arima, "Statistics", "One model per series (seasonal ARIMA)", "Own history"],
    ["LightGBM", HEX.lgb, "Machine learning", "One model trained across all items, predicts each item", "History + price, calendar, SNAP"],
    ["Chronos", HEX.chronos, "AI foundation model", "Pre-trained by Amazon, zero-shot: no training on our data", "Own history"],
    ["Ensemble", HEX.ens, "Combination", "Unweighted average of AutoETS and LightGBM", "Their two forecasts"],
    ["Seasonal naive", HEX.naive, "Benchmark", "Repeats the same weekday last week", "Last week"],
    ["Claude (experiment)", HEX.claude, "General-purpose AI", "Reads sales as text and reasons; 112 series only", "History + price, calendar"],
  ].map(([m, col, fam, fit, sees]) => [
    { text: m, options: { bold: true, color: col } }, { text: fam }, { text: fit }, { text: sees }]);
  s.addTable([hdr, ...rowsM], { x: 0.6, y: 1.5, w: 12.1, colW: [2.1, 2.4, 4.6, 3.0], fontSize: 15, color: HEX.ink,
    border: { type: "solid", pt: 0.75, color: HEX.line }, rowH: 0.5, valign: "middle", margin: 0.08, objectName: "models table" });
  card(s, 0.6, 6.1, 12.1, 0.7, "inputs note");
  text(s, [{ text: "Inputs differ: ", options: { bold: true } },
           { text: "AutoETS, AutoARIMA and Chronos see only each series' own history; LightGBM and Claude also see prices and the calendar." }],
       { x: 0.9, y: 6.1, w: 11.6, h: 0.7, fontSize: 14, color: C.text2, valign: "middle" });
  s.addNotes("SPEAKER 2 (1:05)\n\nWe compared five models. AutoETS and AutoARIMA are classic time series models: they fit one model to each product's own history, with a weekly cycle.\n\nLightGBM is the dominant approach for this kind of retail data. It is one machine-learning model trained across all products at once, which then predicts each product. It also sees prices, holidays and food-stamp days.\n\nChronos is Amazon's pre-trained AI model for time series, trained on about 100 billion data points from energy, traffic, weather and more. It was not trained on our data: the Chronos paper keeps M5, and every retail dataset it uses, out of training as held-out tests. Seasonal naive, 'same weekday last week', is the benchmark.\n\nWe also test the simplest possible combination: an unweighted average of AutoETS and LightGBM. And as an experiment, a second AI joins on a subset of series: Claude, a general-purpose language model, which we'll come back to later. Note that the inputs differ: only LightGBM and Claude see prices and the calendar.\n\nTRANSITION: So which model is best, and at what? Here's the scorecard.");

  s = pres.addSlide({ masterName: "Content", sectionTitle: "Models and results" });
  s.addText("Traditional wins accuracy; AI wins speed", { placeholder: "title" });
  {
    const A = DATA.acc, MT = DATA.mape_total, IR = DATA.item_rmsse;
    const rows = [
      ["Ensemble (AutoETS + LightGBM)", HEX.ens, A.Ensemble, MT.Ensemble, IR.Ensemble, "~3 min", "Yes"],
      ["LightGBM", HEX.lgb, A.LightGBM, MT.LightGBM, IR.LightGBM, "80 s", "Yes"],
      ["AutoETS", HEX.ets, A.AutoETS, MT.AutoETS, IR.AutoETS, "86 s", "Yes"],
      ["AutoARIMA", HEX.arima, A.AutoARIMA, MT.AutoARIMA, IR.AutoARIMA, "39 min", "Yes"],
      ["Chronos (AI)", HEX.chronos, A.Chronos, MT.Chronos, IR.Chronos, "10 s", "None"],
      ["Seasonal naive (benchmark)", HEX.naive, A.SeasonalNaive, MT.SeasonalNaive, IR.SeasonalNaive, "<1 s", "None"],
    ];
    const contenders = rows.slice(0, 5);
    const minOf = k => Math.min(...contenders.map(r => r[k]));
    const best = { 2: minOf(2), 3: minOf(3), 4: minOf(4) };
    const WIN = "DDF2E3";
    const hdr = ["Model", "Overall accuracy\n(WRMSSE)", "Store totals\n(daily error)", "Single items\n(RMSSE)", "Time for\nall series", "Training\nneeded"]
      .map(t => ({ text: t, options: { bold: true, color: "FFFFFF", fill: { color: HEX.navy }, align: "center" } }));
    hdr[0].options.align = "left";
    const body = rows.map((r, i) => {
      const bench = i === 5;
      const cell = (txt, win) => ({ text: txt, options: { align: "center", bold: win, fill: { color: win ? WIN : "FFFFFF" }, color: bench ? HEX.grey : HEX.ink } });
      return [
        { text: r[0], options: { bold: true, color: r[1] } },
        cell(r[2].toFixed(3), !bench && r[2] === best[2]),
        cell(r[3].toFixed(1) + "%", !bench && r[3] === best[3]),
        cell(r[4].toFixed(2), !bench && Math.abs(r[4] - best[4]) < 0.005 && r[4] <= best[4] + 0.0),
        cell(r[5], i === 4),
        cell(r[6], i === 4),
      ];
    });
    s.addTable([hdr, ...body], { x: 0.6, y: 1.5, w: 12.1, colW: [3.4, 1.85, 1.85, 1.75, 1.65, 1.6], fontSize: 15, color: HEX.ink,
      border: { type: "solid", pt: 0.75, color: HEX.line }, rowH: [0.75, 0.55, 0.55, 0.55, 0.55, 0.55, 0.55], valign: "middle", margin: 0.08, objectName: "scorecard table" });
    text(s, "Green = best in its column (benchmark excluded)", { x: 0.6, y: 5.5, w: 12.1, h: 0.3, fontSize: 11, color: HEX.grey, align: "right" });
    card(s, 0.6, 5.85, 12.1, 1.05, "scorecard summary");
    text(s, [{ text: "How to read: ", options: { bold: true, color: HEX.ink } }, { text: "RMSSE = error vs a naive \u201csame as yesterday\u201d forecast; WRMSSE = RMSSE weighted by dollar sales. Smaller is better.", options: { breakLine: true } },
             { text: "Best traditional choice: ", options: { bold: true, color: HEX.ens } }, { text: "the AutoETS + LightGBM average, for accuracy.   " },
             { text: "Best AI strength: ", options: { bold: true, color: HEX.chronos } }, { text: "Chronos, for speed with no training." }],
         { x: 0.9, y: 5.85, w: 11.6, h: 1.05, fontSize: 14, color: C.text1, valign: "middle", paraSpaceAfter: 4 });
  }
  s.addNotes("SPEAKER 2 (1:00)\n\nHere is the comparison: traditional models against AI, on four questions. A quick guide first. RMSSE compares a model's errors with a naive \"same as yesterday\" forecast for the same product, and WRMSSE combines that score across all products, weighted by dollar sales. The store-totals column is the average daily percentage error. In every accuracy column, smaller is better. So, who is most accurate overall? A traditional model: the simple average of AutoETS and LightGBM, with LightGBM alone in second. Who forecasts store totals best? Again, the traditional models. For single products, it's close, and the AI is level with LightGBM. And who is fastest? The AI, Chronos, by far: seconds instead of minutes, with no training at all.\n\nSo from a traditional point of view, the best choice is the AutoETS-plus-LightGBM average, and the AI's real strength is speed. The green cells show the winner of each column.\n\nPOINT AT: the green cells, column by column.\n\nTRANSITION: Let's see what those forecasts actually look like.");

  s = pres.addSlide({ masterName: "Content", sectionTitle: "Models and results" });
  s.addText("Traditional tracks the peaks; the AI runs low", { placeholder: "title" });
  {
    const T = DATA.test;
    s.addChart(pres.charts.LINE, [
      { name: "Actual sales", labels: T.labels, values: T.y }, { name: "Ensemble (traditional)", labels: T.labels, values: T.Ensemble },
      { name: "AutoARIMA (traditional)", labels: T.labels, values: T.AutoARIMA }, { name: "Chronos (AI)", labels: T.labels, values: T.Chronos },
    ], { x: 0.6, y: 1.5, w: 8.2, h: 4.9, ...chartText, chartColors: [HEX.ink, HEX.ens, HEX.arima, HEX.chronos],
      lineSize: 2.25, lineDataSymbol: "none", showLegend: true, legendPos: "b", legendFontSize: 12, legendColor: HEX.ink,
      valAxisLabelFormatCode: "#,##0", valAxisMinVal: 9000, catAxisLabelFrequency: 7, catAxisLabelRotate: 0, catAxisMajorTickMark: "none",
      showTitle: true, title: "Total daily units, all 4 stores, during the 28-day test window", objectName: "forecast chart" });
    [["Follows the peaks", "The traditional average rises and falls with every weekend", HEX.ens],
     ["Flat line", "AutoARIMA's product-by-product forecasts add up to a flat total", HEX.arima],
     ["Right shape, too low", "Chronos sees the weekly rhythm but forecasts about 11% low", HEX.chronos]].forEach(([h, b, col], i) => {
      const y = 1.6 + i * 1.55;
      card(s, 9.1, y, 3.6, 1.35, "forecast note " + i);
      text(s, h, { x: 9.35, y: y + 0.12, w: 3.2, h: 0.45, fontSize: 17, bold: true, color: col, fontFace: THEME.headFontFace });
      text(s, b, { x: 9.35, y: y + 0.6, w: 3.2, h: 0.7, fontSize: 13, color: C.text1, valign: "top" });
    });
  }
  s.addNotes("SPEAKER 2 (1:00)\n\nHere's what that looks like. The black line is actual daily sales across all four stores during the test month. The traditional average, in teal, rises and falls with every weekend peak. AutoARIMA, in green, is almost flat, and Chronos, in orange, has the right shape but sits too low.\n\nWhy? AutoARIMA and Chronos look at one product at a time. For a product that sells a unit or two a day, the best guess is a flat line, and thousands of flat lines added up miss the weekend. LightGBM learns from all products together, so it sees the weekend rush, and averaging it with AutoETS smooths out the rest. Zoom into a single product, though, and the lines come together: one product's daily sales are mostly noise.\n\nTRANSITION: So the specialist AI is fast but less accurate. What about a generalist AI that reads and reasons? Speaker 3.");

  // =============== Speaker 3: general LLM experiment, risks and mitigations
  pres.addSection({ title: "LLM experiment" });
  s = pres.addSlide({ masterName: "Content", sectionTitle: "LLM experiment" });
  s.addText("Claude: a language model that reads sales as text", { placeholder: "title" });
  hbar(s, DATA.claude_totals.map(([m, v]) => [`${m}  ${v.toFixed(3)}`, v]),
       r => (r[0].includes("sum of items") ? pale[famColor(r[0])] : famColor(r[0])),
       { x: 0.6, y: 1.5, w: 6.7, h: 4.75, barGapWidthPct: 40, catAxisLabelFontSize: 11, showValue: false, showTitle: true,
         title: "12 store × dept totals, WRMSSE (pale = summed item forecasts)", objectName: "Claude totals chart" });
  text(s, "Chronos vs Claude: both pre-trained, zero-shot", { x: 7.65, y: 1.5, w: 5.1, h: 0.4, fontSize: 15, bold: true, color: C.text2 });
  const vs = [["", "Chronos", "Claude"], ["Trained on", "Time series", "Text"], ["Reads our data as", "Numbers", "Rows of text"],
              ["Returns", "Quantiles", "Forecast + explanation"], ["All 5,748 series", "10 s, free", "Hours; paid per request"]];
  s.addTable(vs.map((r, i) => r.map((c, j) => ({ text: c, options: {
      bold: i === 0 || j === 0, color: i === 0 ? (j === 1 ? HEX.chronos : j === 2 ? HEX.claude : HEX.ink) : HEX.ink,
      fill: { color: i === 0 ? "FFFFFF" : HEX.light } } }))),
    { x: 7.65, y: 2.0, w: 5.05, colW: [1.75, 1.45, 1.85], fontSize: 13, rowH: 0.48, valign: "middle", margin: 0.06,
      border: { type: "solid", pt: 1, color: "FFFFFF" }, objectName: "Chronos vs Claude table" });
  card(s, 7.65, 4.65, 5.05, 1.6, "items result");
  text(s, [{ text: "100 sampled items: ", options: { bold: true } },
           { text: "AutoETS 0.938 best, AutoARIMA 0.951, Claude 0.958. Same items for every model." }],
       { x: 7.9, y: 4.65, w: 4.6, h: 1.6, fontSize: 14, color: C.text1, valign: "middle" });
  text(s, "Claude covered a subset to keep cost down: 100 random items + 12 totals, compared on the same series. Totals were also fitted directly for the other models.",
       { x: 0.6, y: 6.35, w: 12.1, h: 0.5, fontSize: 13, color: HEX.grey });
  s.addNotes("SPEAKER 3 (1:15)\n\nNow a generalist AI. We used Claude through its API. For each product, our code sends the past year of daily sales as plain text, one row per day with the date, holidays, food-stamp days and price, plus an instruction: forecast the next 28 days and answer in a fixed format. Claude reads the numbers, reasons about patterns such as weekends and holidays, and sends back 28 daily forecasts with a short explanation. No statistical model is fitted; it works from what it learned in training.\n\nEach request costs money and takes a few seconds, so to keep the cost down we used a subset instead of all 5,748 series: 100 randomly chosen products and the 12 store-by-department totals. Every other model was scored on exactly the same series, and to keep it fair, the other models were also fitted directly on those totals.\n\nHow did it perform? On the store totals, very well: it matched our best traditional forecast, the AutoETS-plus-LightGBM average, and beat every single model, including Chronos. On individual products it was in the pack, behind AutoETS and AutoARIMA. So the generalist AI was more accurate than the specialist one, but far slower and more costly to run at scale.\n\nPOINT AT: the Claude bars at the top of the chart, then the comparison table.\n\nTRANSITION: Using a language model also brings a specific risk.");

  s = pres.addSlide({ masterName: "Content", sectionTitle: "LLM experiment" });
  s.addText("Using an LLM to forecast: risks and safeguards", { placeholder: "title" });
  const risks = [
    [I.blind, "Pre-training contamination", "M5 is public and may be in Claude's training data", "Named vs blind test: names, dates and year removed. Accuracy unchanged (0.579 vs 0.583)"],
    [I.shuffle, "Unstable output", "Answers can vary between runs", "Fixed prompt and model; every response saved and cached"],
    [I.coins, "Cost and scale", "Paid per request; slow at scale", "Tested a subset (100 items + 12 totals); same subset for every model"],
    [I.code, "Malformed answers", "Wrong length or format", "Required a fixed JSON format, checked 28 days returned, retried on failure"],
  ];
  text(s, "Risk", { x: 1.6, y: 1.45, w: 4.5, h: 0.35, fontSize: 13, bold: true, color: HEX.grey });
  text(s, "What we did", { x: 6.7, y: 1.45, w: 6.0, h: 0.35, fontSize: 13, bold: true, color: HEX.grey });
  risks.forEach(([img, h, why, did], i) => {
    const y = 1.85 + i * 1.0;
    card(s, 0.6, y, 12.1, 0.88, "risk " + i);
    badge(s, img, HEX.claude, 0.78, y + 0.12, 0.64, h);
    text(s, [{ text: h, options: { bold: true, breakLine: true } }, { text: why, options: { color: HEX.grey } }],
         { x: 1.6, y, w: 4.9, h: 0.88, fontSize: 14, color: C.text2, valign: "middle" });
    text(s, did, { x: 6.7, y, w: 5.8, h: 0.88, fontSize: 14, color: C.text1, valign: "middle" });
  });
  card(s, 0.6, 5.95, 12.1, 0.85, "contamination caveat", HEX.navy);
  badge(s, I.warn, HEX.amber, 0.78, 6.05, 0.64, "caveat");
  text(s, "The blind test reduces identity cues, but it cannot guarantee that contamination is excluded: the sales pattern itself could be recognised.",
       { x: 1.6, y: 5.95, w: 10.9, h: 0.85, fontSize: 15, bold: true, color: "FFFFFF", valign: "middle" });
  s.addNotes("SPEAKER 3 (1:00)\n\nThe obvious worry: M5 is public data, so Claude may have seen these exact sales during training, and be remembering rather than forecasting. So we ran a blind test. Every forecast was made twice: once with the real labels, meaning Walmart, the store and product IDs, and the real dates; and once with all of that hidden, just 'day 1, day 2' with no names and no year.\n\nThink of it as a blind taste test. It's the same idea as a permutation test in statistics: if the labels carry no information, taking them away shouldn't change the result. And it didn't: accuracy was practically identical with and without the labels, 0.579 versus 0.583. Knowing it was Walmart in 2016 gave Claude no advantage.\n\nWe also saved every response so the results can be re-checked, and checked that every answer came back in the right format. One honest limit remains: hiding the labels can't hide the sales pattern itself. If Claude had memorised the shape of these series, a blind test couldn't catch it, so contamination can't be fully ruled out.\n\nIF ASKED (permutation test): it is the same idea, not a formal permutation test. A real one reshuffles labels many times to get a p-value; we made one with-labels vs without-labels comparison.\n\nBACKGROUND (not to read aloud): Our code asked Claude for 28 daily forecasts in a fixed JSON format. We checked each reply had exactly 28 days and retried automatically if not. 224 requests = 112 series x 2 versions (named and blind); all came back usable. Every reply is saved in our repo.\n\nTRANSITION: Speaker 4 will wrap up and show the dashboard.");

  // =============== Speaker 4: answer, limitations (incl. the newsvendor business problem), demo
  pres.addSection({ title: "Answer and demo" });
  s = pres.addSlide({ masterName: "Closing Dark", sectionTitle: "Answer and demo" });
  s.addText("Our answer: not yet on accuracy, yes on speed", { placeholder: "title" });
  const take = [
    [I.lgb, HEX.lgb, "Traditional methods lead on accuracy", "LightGBM, AutoETS and their average are the three best"],
    [I.chronos, HEX.chronos, "Chronos wins on speed", "10 s for all series, no training"],
    [I.claude, HEX.claude, "Claude matched the best on totals", "Promising, but tested on 112 series only"],
  ];
  take.forEach(([img, col, h, b], i) => {
    const y = 1.6 + i * 1.35;
    badge(s, img, col, 0.6, y, 0.8, h);
    text(s, h, { x: 1.6, y, w: 5.4, h: 0.45, fontSize: 19, bold: true, color: C.background1 });
    text(s, b, { x: 1.6, y: y + 0.48, w: 5.4, h: 0.45, fontSize: 14, color: C.background2 });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 7.3, y: 1.5, w: 5.4, h: 5.0, rectRadius: 0.12, fill: { color: HEX.tint }, line: { color: HEX.tint }, objectName: "limitations card" });
  badge(s, I.warn, HEX.amber, 7.6, 1.75, 0.65, "limitations");
  text(s, "Limitations", { x: 8.4, y: 1.75, w: 4.0, h: 0.65, fontSize: 19, bold: true, color: C.background1, valign: "middle" });
  text(s, [
    { text: "One 28-day test window: close rankings could flip in another month.", options: { bullet: true, breakLine: true } },
    { text: "Claude: 112 series only; the blind test can't fully rule out contamination.", options: { bullet: true, breakLine: true } },
    { text: "Accuracy is not the business goal. Ordering is a newsvendor problem: running out costs the margin (underage), unsold food costs its price (overage). The best order is a margin-set quantile, not the forecast, and our accuracy metrics weigh both errors equally.", options: { bullet: true } },
  ], { x: 7.6, y: 2.6, w: 4.9, h: 3.7, fontSize: 14, color: C.background2, paraSpaceAfter: 8, valign: "top" });
  s.addNotes("SPEAKER 4 (1:45)\n\nSo, can AI foundation models beat traditional methods? Our answer: not yet on accuracy, yes on speed. LightGBM, AutoETS and their simple average were the three most accurate. Chronos was the clear winner on speed: ten seconds, no training. And Claude matched the best traditional approach on store totals.\n\nOur results have limits. First, Claude was tested on a subset, and our blind test can't fully rule out that it saw this public data. Second, sales are not demand: when a shelf is empty, sales show zero even if customers wanted the product.\n\nAnd the most important limitation for a business: accuracy isn't the real goal. Ordering stock is a newsvendor problem with two different costs. If you order too little, you lose the margin on every sale you miss; that's the underage cost. If you order too much, unsold food is wasted at its cost; that's the overage cost. Because those costs depend on the margin, the best order isn't the forecast itself but a quantile of demand, and our accuracy metrics treat over- and under-forecasting the same. So what happened when we turned each model's forecasts into actual orders? For most products, it barely mattered which model we used: the profit differences were small enough to be luck. Only for high-margin products, where running out of stock is expensive, did the more accurate model, LightGBM, clearly make more money.\n\nSo our recommendation: average a statistical model like AutoETS with LightGBM, use Chronos where speed or a lack of training data matters, and choose models on the metric that matches the business decision. Our next step is a rolling backtest over several windows.\n\nLet me show you the business problem in our dashboard.\n\nTRANSITION: click the screenshot on the next slide.");

  s = pres.addSlide({ masterName: "Content", sectionTitle: "Answer and demo" });
  s.addText("Demo: Shelf Signal dashboard", { placeholder: "title" });
  const SHOT = process.argv[4];
  const LIVE = "https://shihan-2002.github.io/shelf-signal-dashboard/#planner";
  s.addShape(pres.shapes.RECTANGLE, { x: 0.6, y: 1.5, w: 7.2, h: 4.78, fill: { color: "FFFFFF" }, line: { color: HEX.line, width: 1 }, objectName: "screenshot frame" });
  s.addImage({ path: SHOT, x: 0.62, y: 1.52, w: 7.16, h: 4.74, hyperlink: { url: LIVE, tooltip: "Open the live dashboard" },
    altText: "Shelf Signal order planner: demand distribution, order quantity and profit by model", objectName: "dashboard screenshot" });
  text(s, [{ text: "Open live dashboard ↗", options: { hyperlink: { url: LIVE, tooltip: "Opens in your browser" }, bold: true, color: HEX.lgb } },
           { text: "   ·   ", options: { color: HEX.grey } },
           { text: "shihan-2002.github.io/shelf-signal-dashboard", options: { hyperlink: { url: LIVE }, color: HEX.lgb } }],
       { x: 0.6, y: 6.35, w: 7.2, h: 0.4, fontSize: 13 });
  const demo = [
    [I.play, "Forecast explorer", "One store's department: every model against actual sales"],
    [I.layers, "AI lab", "Claude's own reasoning, and the named-vs-blind test"],
    [I.sliders, "Order planner", "Change the margin: the order moves between P20 and P80"],
  ];
  demo.forEach(([img, h, b], i) => {
    const y = 1.55 + i * 1.3;
    badge(s, img, HEX.navy, 8.4, y + 0.05, 0.75, h);
    text(s, h, { x: 9.35, y, w: 3.4, h: 0.45, fontSize: 17, bold: true, color: C.text2, valign: "bottom" });
    text(s, b, { x: 9.35, y: y + 0.48, w: 3.4, h: 0.7, fontSize: 14, color: C.text1, valign: "top" });
  });
  text(s, "Thank you — questions?", { x: 8.4, y: 5.55, w: 4.3, h: 0.7, fontSize: 26, bold: true, color: HEX.navy, fontFace: THEME.headFontFace });
  s.addNotes("SPEAKER 4 (1:30 demo + 0:15 close)\n\n[Click the screenshot to open the dashboard. If the internet fails, play the screen recording.]\n\n(0:00-0:20) FORECAST EXPLORER. This is Shelf Signal, which extends our teammate's original dashboard with all our models. Here's one store's department total: the black line is actual sales, and you can switch each model on and off. The ensemble and LightGBM follow the weekend peaks; Chronos runs low.\n\n(0:20-0:40) AI LAB. Here Claude explains its own forecast in plain English, and this chart is the named-versus-blind test: every point sits on the diagonal, so real names gave it no advantage.\n\n(0:40-1:30) ORDER PLANNER. Now the business problem. For this item, the model forecasts about eight units for the day. At a 50% margin, the best order is the median of demand. Drop the margin to 20%: a wasted unit now costs four times a lost sale, so the order falls. Raise it to 80%: a lost sale costs four times a wasted unit, so we order more. Same forecast, different decision. The table scores every model's orders against actual sales: the profit ranking isn't the same as the accuracy ranking, and at typical margins the differences are small.\n\n(close) That's our project: traditional methods still lead on accuracy, AI wins on speed, and the right order depends on your costs. Thank you, and we're happy to take questions.\n\n[Press Cmd+Tab to return to the slides for Q&A.]");

  await pres.writeFile({ fileName: OUT });
  await applyTheme(OUT, THEME);
  console.log("wrote", OUT);
}
main().catch(e => { console.error(e); process.exit(1); });
