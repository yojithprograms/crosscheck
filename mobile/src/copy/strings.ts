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
  placeholders: {
    map: { title: "Map", body: "Your school's risk map will appear here." },
    route: { title: "Route", body: "Plan a lower-risk route to school here." },
    report: { title: "Report a close call", body: "Close-call reports will start here." },
    school: { title: "School safety summary", body: "Your school's safety summary will appear here." },
    settings: { title: "Settings", body: "Settings will appear here." },
  },
  launch: { loading: "Loading…" },
} as const;
