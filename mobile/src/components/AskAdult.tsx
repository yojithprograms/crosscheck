import { StyleSheet, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { EmptyState } from "@/components/EmptyState";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";

/**
 * Shown every time the app opens after someone answered "Under 13" (DESIGN.md §10.1). There is no way
 * forward from this screen, and the answer is saved on the device.
 */
export function AskAdult() {
  const insets = useSafeAreaInsets();
  return (
    <View style={[styles.screen, { paddingTop: insets.top, paddingBottom: insets.bottom }]}>
      <EmptyState icon="people-outline" title={strings.askAdult.title} body={strings.askAdult.body} />
    </View>
  );
}

const styles = StyleSheet.create({ screen: { flex: 1, backgroundColor: colors.bg } });
