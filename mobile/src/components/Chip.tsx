import { Ionicons } from "@expo/vector-icons";
import type { ComponentProps } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";
import { type } from "@/theme/type";

type ChipProps = {
  label: string;
  selected: boolean;
  onPress: () => void;
  icon?: ComponentProps<typeof Ionicons>["name"];
};

/** A pill button for choices (age, travel mode, layer toggles). Selected chips are filled teal. */
export function Chip({ label, selected, onPress, icon }: ChipProps) {
  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityState={{ selected }}
      style={[styles.chip, selected && styles.selected]}
    >
      {icon ? <Ionicons name={icon} size={18} color={selected ? colors.onBrand : colors.text} /> : null}
      <Text style={[styles.label, selected && styles.selectedLabel]}>{label}</Text>
    </Pressable>
  );
}

type GroupProps<T extends string> = {
  options: { value: T; label: string; icon?: ChipProps["icon"] }[];
  value: T | null;
  onChange: (value: T) => void;
};

/** A row of chips where at most one is selected. Nothing is selected unless `value` says so. */
export function ChipGroup<T extends string>({ options, value, onChange }: GroupProps<T>) {
  return (
    <View style={styles.group}>
      {options.map((option) => (
        <Chip
          key={option.value}
          label={option.label}
          icon={option.icon}
          selected={option.value === value}
          onPress={() => onChange(option.value)}
        />
      ))}
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {
    minHeight: shape.minTouchTarget,
    paddingHorizontal: spacing.lg,
    borderRadius: 999,
    borderWidth: 1.5,
    borderColor: colors.border,
    backgroundColor: colors.bg,
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.xs,
  },
  selected: { backgroundColor: colors.brand, borderColor: colors.brand },
  label: { ...type.body, color: colors.text },
  selectedLabel: { color: colors.onBrand, fontWeight: "600" },
  group: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
});
