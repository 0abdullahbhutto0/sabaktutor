import React, { ReactNode } from 'react';
import { Pressable, StyleSheet, Text, ViewStyle, TextStyle } from 'react-native';
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
}: ChunkyButtonProps) {
  
  const handlePress = () => {
    if (disabled) return;
    try {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
    } catch (e) {}
    onPress();
  };

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
  disabled: {
    opacity: 0.5,
  },
  text: {
    color: '#ffffff',
    fontSize: 16,
    fontWeight: '700',
  },
  textPressed: {
    // Optional additional text style on press
  }
});
