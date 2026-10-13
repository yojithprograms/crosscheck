import { Stack } from "expo-router";

/** First-run screens: Welcome (S1), Before you start (S2), Choose your school (S3). No headers. */
export default function OnboardingLayout() {
  return <Stack screenOptions={{ headerShown: false }} />;
}
