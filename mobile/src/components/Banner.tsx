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

const palette = {
  info: { bg: colors.infoBg, fg: colors.infoText },
  warn: { bg: colors.warnBg, fg: colors.warnText },
  error: { bg: colors.errorBg, fg: colors.errorText },
} as const;

/** A message strip just under the header: info, warning, or error, with an optional action. */
export function Banner({ kind, text, actionLabel, onAction }: Props) {
  const { bg, fg } = palette[kind];
  return (
    <View style={[styles.banner, { backgroundColor: bg }]} accessibilityRole="alert">
      <Text style={[styles.text, { color: fg }]}>{text}</Text>
      {actionLabel && onAction ? (
        <Pressable onPress={onAction} accessibilityRole="button" style={styles.action} hitSlop={8}>
          <Text style={[styles.actionText, { color: fg }]}>{actionLabel}</Text>
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
    paddingVertical: spacing.sm,
    gap: spacing.md,
  },
  text: { ...type.caption, flex: 1 },
  action: { minHeight: shape.minTouchTarget, justifyContent: "center" },
  actionText: { ...type.headline, textDecorationLine: "underline" },
});
