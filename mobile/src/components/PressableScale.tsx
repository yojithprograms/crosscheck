import { useRef, useState } from "react";
import { Animated, Pressable, type PressableProps, type StyleProp, type ViewStyle } from "react-native";

const AnimatedPressable = Animated.createAnimatedComponent(Pressable);

type Props = Omit<PressableProps, "style"> & {
  style?: StyleProp<ViewStyle>;
  pressedStyle?: StyleProp<ViewStyle>; // merged into `style` while a finger is down
  scaleTo?: number; // how small it gets when pressed (1 = no shrink)
};

/**
 * A Pressable that shrinks a little under your finger and springs back, so taps feel responsive.
 * Uses React Native's built-in Animated (no extra library), running on the native thread.
 */
export function PressableScale({ style, pressedStyle, scaleTo = 0.97, onPressIn, onPressOut, disabled, ...rest }: Props) {
  const scale = useRef(new Animated.Value(1)).current;
  const [pressed, setPressed] = useState(false);

  const springTo = (toValue: number) =>
    Animated.spring(scale, { toValue, useNativeDriver: true, speed: 40, bounciness: 0 }).start();

  return (
    <AnimatedPressable
      {...rest}
      disabled={disabled}
      onPressIn={(event) => {
        setPressed(true);
        springTo(scaleTo);
        onPressIn?.(event);
      }}
      onPressOut={(event) => {
        setPressed(false);
        springTo(1);
        onPressOut?.(event);
      }}
      style={[style, pressed && !disabled ? pressedStyle : null, { transform: [{ scale }] }]}
    />
  );
}
