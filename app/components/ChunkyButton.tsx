import React, { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, View, ViewStyle, TextStyle } from 'react-native';
import * as Haptics from 'expo-haptics';

interface ChunkyButtonProps {
  onPress: () => void;
  title?: string;
  children?: ReactNode;
  style?: ViewStyle | ViewStyle[];
  textStyle?: TextStyle | TextStyle[];
  color?: string;
  shadowColor?: string;
  disabled?: boolean;
  chunky?: boolean;
}

export default function ChunkyButton({ 
  onPress, 
  title, 
  children, 
  style, 
  textStyle,
  color = '#206b38',
  shadowColor = '#104d23',
  disabled = false,
  chunky = false,
}: ChunkyButtonProps) {
  
  const handlePress = () => {
    if (disabled) return;
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch (e) {}
    onPress();
  };

  const flatStyle = StyleSheet.flatten(style) || {};
  const radius = (flatStyle as any).borderRadius ?? 12;

  if (chunky) {
    return (
      <View style={[{ borderRadius: radius }, disabled && styles.disabled]}>
        <View style={[
          styles.shadowLayer,
          { backgroundColor: shadowColor, borderRadius: radius },
        ]} />
        <Pressable 
          onPress={handlePress}
          disabled={disabled}
          style={({ pressed }) => [
            styles.button,
            { backgroundColor: color, borderRadius: radius, borderColor: shadowColor, borderWidth: 2, borderBottomWidth: 4 },
            style,
            pressed && [styles.chunkyPressed, { borderRadius: radius }],
          ]}
        >
          {({ pressed }) => (
            <>
              {title ? (
                <Text style={[styles.text, textStyle]}>{title}</Text>
              ) : (
                children
              )}
            </>
          )}
        </Pressable>
      </View>
    );
  }

  return (
    <Pressable 
      onPress={handlePress}
      disabled={disabled}
      style={({ pressed }) => [
        styles.button,
        { backgroundColor: color, borderBottomColor: shadowColor },
        style,
        pressed && styles.pressed,
        disabled && styles.disabled,
      ]}
    >
      {({ pressed }) => (
        <>
          {title ? (
            <Text style={[styles.text, textStyle, pressed && styles.textPressed]}>{title}</Text>
          ) : (
            children
          )}
        </>
      )}
    </Pressable>
  );
}

const styles = StyleSheet.create({
  shadowLayer: {
    position: 'absolute',
    top: 3,
    left: 0,
    right: 0,
    bottom: -3,
  },
  button: {
    paddingVertical: 16,
    paddingHorizontal: 24,
    borderRadius: 8,
    alignItems: 'center',
    justifyContent: 'center',
    borderBottomWidth: 4,
    flexDirection: 'row',
  },
  pressed: {
    borderBottomWidth: 0,
    marginTop: 4,
  },
  chunkyPressed: {
    borderBottomWidth: 2,
    marginTop: 2,
  },
  disabled: {
    opacity: 0.5,
  },
  text: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  textPressed: {},
});

