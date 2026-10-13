// All user-facing text lives here (CLAUDE.md hard rule). UI copy says "lower-risk", never "safe".
export const strings = {
  appName: "CrossCheck",
  tabs: { map: "Map", route: "Route", report: "Report", school: "School" },
  header: { settings: "Settings" },
  banner: {
    waking: "Waking up the server… this can take up to a minute.",
    offline: "You're offline. Some things won't load.",
    unreachable: "Can't reach CrossCheck right now.",
    retry: "Retry",
  },
  launch: { loading: "Loading…" },

  // S1 · Welcome
  welcome: {
    title: "Find a lower-risk way to school",
    illustrationLabel: "A small map with a red high-risk street and a blue lower-risk route",
    rows: [
      { icon: "map-outline", text: "See which streets near your school have the most crashes" },
      { icon: "navigate-outline", text: "Compare the fastest route with a lower-risk one" },
      { icon: "megaphone-outline", text: "Report close calls so they count" },
    ],
    next: "Next",
  },

  // S2 · Before you start
  promise: {
    title: "Before you start",
    privacyTitle: "Your privacy",
    privacy:
      "No account needed. We never save your home address. Photos have their location info removed. Photos showing faces or license plates are never saved or shown.",
    safetyTitle: "Your safety",
    safety:
      "Lower-risk doesn't mean risk-free. Always follow crossing guards, signals, and your family's rules. Never use your phone while crossing or riding.",
    aiTitle: "AI",
    ai: "CrossCheck uses AI (Claude, made by Anthropic) to sort near-miss reports. You always get to check and fix what it picks.",
    ageQuestion: "How old are you?",
    ageUnder13: "Under 13",
    age13Plus: "13 or older",
    understand: "I understand",
  },
  askAdult: {
    title: "Ask an adult",
    body: "CrossCheck is for students 13 and older for now. Ask a parent or guardian to set it up on their phone and use it with you.",
  },

  // S3 · Choose your school
  schoolPicker: {
    title: "Which school do you go to?",
    searchPlaceholder: "Search schools",
    searchLabel: "Search schools",
    levels: { ES: "Elementary", MS: "Middle", HS: "High" },
    coverage: (count: number) => `CrossCheck covers ${count} ${count === 1 ? "school" : "schools"} right now.`,
    noMatches: "No schools match that search.",
    continue: "Continue",
    save: "Save",
    unreachableTitle: "Can't reach CrossCheck",
    unreachableBody: "Check your connection, then try again.",
    tryAgain: "Try again",
    loading: "Loading schools…",
  },

  months: ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],

  risk: {
    high: "High risk",
    medium: "Medium risk",
    low: "Lower risk",
    percentile: (p: number) => `Riskier than ${p}% of Fairfax-area streets`,
  },

  crash: {
    severity: { K: "Fatal", A: "Serious injury", B: "Visible injury", C: "Injury (not visible)", O: "No injury" },
  },

  // S4 · Map
  map: {
    layers: { risk: "Risk", crashes: "Crashes", reports: "Reports" },
    legend: { high: "High risk", medium: "Medium risk", crash: "Crash", report: "Student report" },
    planRoute: "Plan my route",
    reportCloseCall: "Report a close call",
    loadError: "Couldn't load the map data",
    retry: "Retry",
    notReadyTitle: "This school's map isn't ready yet",
    notReadyBody: "Pick a different school to keep going.",
    changeSchool: "Change school",
    loadingMap: "Loading the map…",
    howScoresWork: "How risk scores work",
    schoolMarker: (name: string) => `${name} entrance`,
    crashMarker: (mode: "ped" | "bike", year: number) =>
      `${mode === "ped" ? "Crash involving someone walking" : "Crash involving someone biking"}, ${year}`,
  },

  // S6 · Start and S7 · Pin picker
  start: {
    title: (school: string) => `Plan your route to ${school}`,
    usualTitle: "My usual route",
    usualBody: (mode: string) => `Saved start point · ${mode}`,
    useIt: "Use it",
    whereTitle: "Where are you starting?",
    useLocation: "Use my location",
    findingLocation: "Finding your location…",
    dropPin: "Drop a pin on the map",
    modes: { walk: "Walk", bike: "Bike / Scooter" },
    tip: "Drop the pin near home. It doesn't have to be exact, and we don't save it.",
    locationOff: "Location is off. You can drop a pin instead.",
    locationUnavailable: "We couldn't find your location. You can drop a pin instead.",
    outside: (school: string) => `That's outside the area CrossCheck covers for ${school}.`,
  },
  pin: {
    back: "Back",
    instruction: "Move the map so the pin is near where you start.",
    moveInside: "Move the pin inside the circle.",
    startHere: "Start here",
    pinLabel: "Start point pin, fixed in the center of the map",
  },
  // Temporary until Step 4.2 builds the route results (S8).
  pickedStart: {
    title: "Start point chosen",
    body: (miles: string, school: string) => `About ${miles} from ${school}. Route results are the next step.`,
    changeStart: "Change start",
  },

  // S5 · Detail cards
  cards: {
    close: "Close",
    why: "Why",
    noReasons: "This street ranks above most nearby streets overall.",
    preliminary: (count: number) => `Includes ${count} from 2026 (preliminary data).`,
    speedLimit: "Speed limit",
    lanes: "Lanes",
    sidewalk: "Sidewalk",
    sidewalkValues: { yes: "Yes", partly: "Partly", no: "No", unknown: "Unknown" },
    mph: (value: string) => `${value} mph`,
    reportsHere: (count: number) => `Student reports here: ${count} in the last 6 months.`,
    howCalculated: "How is this calculated?",
    loading: "Loading…",
    loadError: "Couldn't load this street.",
    retry: "Retry",
    crashTitle: (mode: "ped" | "bike") =>
      mode === "ped" ? "Crash involving someone walking" : "Crash involving someone biking",
    crashSource: "Source: VDOT crash data.",
    crashPreliminary: "Preliminary — may change.",
  },

  // S19 · How risk scores work
  howItWorks: {
    title: "How risk scores work",
    sections: [
      {
        title: "What the colors mean",
        body: "Red streets are riskier than 90% of streets in the Fairfax area. Amber streets are riskier than 70%.",
      },
      {
        title: "What CrossCheck looks at",
        body: "Speed limits, number of lanes, sidewalks, traffic signals, how many cars use the road, the type of road, and where people walking or biking were hit before.",
      },
    ],
    testedTitle: "How we tested it",
    tested: (capture: number) =>
      `We trained on crashes from 2017–2020 and checked whether it could predict where crashes happened in 2021–2024, in parts of the county it hadn't seen. The 10% of streets it ranked riskiest had ${capture}% of those crashes.`,
    routesTitle: "How lower-risk routes work",
    routes: "Risky streets count as longer than they really are, so the route finder goes around them when the detour is short enough.",
    limitsTitle: "What it can't know",
    limits: (dataThrough: string) =>
      `It doesn't know how many people walk each street, crash data runs through ${dataThrough}, and values marked ≈ are estimates. Lower-risk isn't risk-free.`,
    loading: "Loading…",
    loadError: "Couldn't load the latest numbers.",
  },

  placeholders: {
    map: { title: "Map", body: "Your school's risk map will appear here." },
    route: { title: "Route", body: "Plan a lower-risk route to school here." },
    report: { title: "Report a close call", body: "Close-call reports will start here." },
    school: { title: "School safety summary", body: "Your school's safety summary will appear here." },
    settings: { title: "Settings", body: "Settings will appear here." },
  },
} as const;
