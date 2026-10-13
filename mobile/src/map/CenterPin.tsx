import { Ionicons } from "@expo/vector-icons";
import { StyleSheet, View } from "react-native";

import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";

const PIN_SIZE = 44;

/**
 * A pin fixed in the middle of the screen (S7). The student moves the map under it, so its tip always
 * marks the center of the map. It sits above the map but lets touches pass through to it.
 */
export function CenterPin({ tint = colors.brand }: { tint?: string }) {
  return (
    <View style={styles.fill} pointerEvents="none">
      <View accessible accessibilityLabel={strings.pin.pinLabel} style={styles.pin}>
        <Ionicons name="location-sharp" size={PIN_SIZE} color={tint} />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  fill: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0, alignItems: "center", justifyContent: "center" },
  // The icon's tip is at its bottom edge, so lift it by half its height to put the tip on the center.
  pin: { marginBottom: PIN_SIZE },
});
