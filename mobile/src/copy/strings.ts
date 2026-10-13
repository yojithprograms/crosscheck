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

  placeholders: {
    map: { title: "Map", body: "Your school's risk map will appear here." },
    route: { title: "Route", body: "Plan a lower-risk route to school here." },
    report: { title: "Report a close call", body: "Close-call reports will start here." },
    school: { title: "School safety summary", body: "Your school's safety summary will appear here." },
    settings: { title: "Settings", body: "Settings will appear here." },
  },
} as const;
