import { Ionicons } from "@expo/vector-icons";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type Props = {
  kind: "info" | "warn" | "error";
  text: string;
  actionLabel?: string;
  onAction?: () => void;
};

// Each kind has its own icon, so the message never relies on color alone.
const palette = {
  info: { bg: colors.infoBg, fg: colors.infoText, icon: "information-circle" },
  warn: { bg: colors.warnBg, fg: colors.warnText, icon: "warning" },
  error: { bg: colors.errorBg, fg: colors.errorText, icon: "alert-circle" },
} as const;

/** A message strip just under the header: info, warning, or error, with an optional action. */
export function Banner({ kind, text, actionLabel, onAction }: Props) {
  const { bg, fg, icon } = palette[kind];
  return (
    <View style={[styles.banner, { backgroundColor: bg }]} accessibilityRole="alert">
      <Ionicons name={icon} size={20} color={fg} />
      <Text style={[styles.text, { color: fg }]}>{text}</Text>
      {actionLabel && onAction ? (
        <Pressable onPress={onAction} accessibilityRole="button" style={styles.action} hitSlop={4}>
          <View style={styles.pill}>
            <Text style={[styles.actionText, { color: fg }]}>{actionLabel}</Text>
          </View>
        </Pressable>
      ) : null}
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: shape.screenPadding,
    paddingVertical: spacing.md,
    gap: spacing.md,
  },
  text: { ...type.caption, fontSize: 14, lineHeight: 19, flex: 1 },
  action: { minHeight: shape.minTouchTarget, justifyContent: "center" },
  pill: {
    backgroundColor: "rgba(255, 255, 255, 0.7)",
    borderRadius: shape.pill,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
  actionText: { ...type.caption, fontSize: 14, fontWeight: "700" },
});
