import { Ionicons } from "@expo/vector-icons";
import { useEffect, useRef, type ReactNode } from "react";
import { Animated, PanResponder, Pressable, ScrollView, StyleSheet, View, useWindowDimensions } from "react-native";

import { strings } from "@/copy/strings";
import { colors } from "@/theme/colors";
import { shape, spacing } from "@/theme/spacing";

const MAX_HEIGHT_SHARE = 0.6; // never taller than 60% of the screen
const SWIPE_CLOSE_DISTANCE = 60; // pixels of downward drag that closes the card

type Props = { visible: boolean; onClose: () => void; children: ReactNode };

/**
 * A panel that slides up over the map. It closes with the X button, by swiping down on its top edge,
 * or when the parent closes it (for example, when the map is tapped).
 */
export function BottomCard({ visible, onClose, children }: Props) {
  const { height } = useWindowDimensions();
  const slide = useRef(new Animated.Value(visible ? 0 : 1)).current; // 0 = shown, 1 = hidden below the edge
  const drag = useRef(new Animated.Value(0)).current;

  useEffect(() => {
    drag.setValue(0);
    Animated.spring(slide, { toValue: visible ? 0 : 1, useNativeDriver: true, bounciness: 0 }).start();
  }, [visible, slide, drag]);

  const swipe = useRef(
    PanResponder.create({
      onMoveShouldSetPanResponder: (_e, g) => g.dy > 6 && Math.abs(g.dy) > Math.abs(g.dx),
      onPanResponderMove: (_e, g) => drag.setValue(Math.max(0, g.dy)),
      onPanResponderRelease: (_e, g) => {
        if (g.dy > SWIPE_CLOSE_DISTANCE) onClose();
        else Animated.spring(drag, { toValue: 0, useNativeDriver: true }).start();
      },
    }),
  ).current;

  const translateY = Animated.add(Animated.multiply(slide, height), drag);

  return (
    <Animated.View
      style={[styles.card, { maxHeight: height * MAX_HEIGHT_SHARE, transform: [{ translateY }] }]}
      pointerEvents={visible ? "auto" : "none"}
      accessibilityViewIsModal={visible}
    >
      <View {...swipe.panHandlers} style={styles.handleArea}>
        <View style={styles.handle} />
      </View>
      <Pressable
        onPress={onClose}
        accessibilityRole="button"
        accessibilityLabel={strings.cards.close}
        style={styles.close}
        hitSlop={8}
      >
        <Ionicons name="close" size={26} color={colors.text} />
      </Pressable>
      <ScrollView contentContainerStyle={styles.content}>{children}</ScrollView>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  card: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: colors.bg,
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    borderWidth: 1,
    borderColor: colors.border,
    elevation: 12,
    shadowColor: "#000",
    shadowOpacity: 0.15,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: -4 },
  },
  handleArea: { height: 28, alignItems: "center", justifyContent: "center" },
  handle: { width: 40, height: 5, borderRadius: 3, backgroundColor: colors.border },
  close: {
    position: "absolute",
    top: 6,
    right: 8,
    width: shape.minTouchTarget,
    height: shape.minTouchTarget,
    alignItems: "center",
    justifyContent: "center",
    zIndex: 2,
  },
  content: { paddingHorizontal: shape.screenPadding, paddingBottom: spacing.xl, gap: spacing.sm },
});
