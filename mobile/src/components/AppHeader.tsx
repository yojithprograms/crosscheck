import { Ionicons } from "@expo/vector-icons";
import { useRouter } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { ServerBanner } from "@/components/ServerBanner";
import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape } from "@/theme/spacing";
import { type } from "@/theme/type";

/** The header used by every tab: title on the left, gear on the right, banners just underneath. */
export function AppHeader({ title }: { title: string }) {
  const insets = useSafeAreaInsets();
  const router = useRouter();
  return (
    <View style={[styles.wrap, { paddingTop: insets.top }]}>
      <View style={styles.row}>
        <Text style={styles.title} accessibilityRole="header">
          {title}
        </Text>
        <Pressable
          onPress={() => router.push("/settings")}
          accessibilityRole="button"
          accessibilityLabel={strings.header.settings}
          style={styles.gear}
          hitSlop={8}
        >
          <Ionicons name="settings-outline" size={26} color={colors.text} />
        </Pressable>
      </View>
      <ServerBanner />
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: { backgroundColor: colors.bg, borderBottomWidth: StyleSheet.hairlineWidth, borderBottomColor: colors.border },
  row: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    paddingLeft: shape.screenPadding,
    paddingRight: 4,
    minHeight: 56,
  },
  title: { ...type.sectionTitle, color: colors.text, flex: 1 },
  gear: { width: shape.minTouchTarget, height: shape.minTouchTarget, alignItems: "center", justifyContent: "center" },
});
