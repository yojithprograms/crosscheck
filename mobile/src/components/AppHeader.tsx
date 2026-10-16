import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { PressableScale } from "@/components/PressableScale";
import { ServerBanner } from "@/components/ServerBanner";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shadow } from "@/theme/shadow";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

/** The header used by every tab: title on the left, a soft round settings button on the right, banners just underneath. */
export function AppHeader({ title }: { title: string }) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  return (
    <View style={[styles.wrap, { paddingTop: insets.top }]}>
      <View style={styles.row}>
        <Text style={styles.title} accessibilityRole="header">
          {title}
        </Text>
        <PressableScale
          onPress={() => router.push("/settings")}
          accessibilityRole="button"
          accessibilityLabel={strings.header.settings}
          style={styles.gear}
          scaleTo={0.9}
          hitSlop={4}
        >
          <Ionicons name="settings-outline" size={22} color={colors.brandDark} />
        </PressableScale>
      </View>
      <ServerBanner />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { backgroundColor: colors.surface, ...shadow.card },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingLeft: shape.screenPadding,
    paddingRight: spacing.md,
    minHeight: 60,
  },
  title: { ...type.sectionTitle, color: colors.text, flex: 1 },
  gear: {
    width: shape.minTouchTarget,
    height: shape.minTouchTarget,
    borderRadius: shape.minTouchTarget / 2,
    backgroundColor: colors.brandTint,
    alignItems: "center",
    justifyContent: "center",
  },
});
