import { Stack } from "expo-router";

/** The report flow (S10 to S15) is a stack inside the Report tab. The tab header stays; the stack adds none. */
export default function ReportLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
