import React, { useRef } from 'react';
import { View, StyleSheet, TouchableOpacity, Modal, PanResponder, Dimensions, SafeAreaView } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import Svg, { Path } from 'react-native-svg';

interface ScratchpadModalProps {
  visible: boolean;
  onClose: () => void;
  paths: string[][];
  setPaths: React.Dispatch<React.SetStateAction<string[][]>>;
}

const { width, height } = Dimensions.get('window');

export const ScratchpadModal: React.FC<ScratchpadModalProps> = ({ visible, onClose, paths, setPaths }) => {
  const currentPathRef = useRef<string[]>([]);
  
  const panResponder = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: (evt) => {
        const { locationX, locationY } = evt.nativeEvent;
        currentPathRef.current = [`M${locationX},${locationY}`];
        setPaths(prev => [...prev, currentPathRef.current]);
      },
      onPanResponderMove: (evt) => {
        const { locationX, locationY } = evt.nativeEvent;
        currentPathRef.current.push(`L${locationX},${locationY}`);
        // We trigger a re-render by replacing the last path in state
        setPaths(prev => {
          const newPaths = [...prev];
          newPaths[newPaths.length - 1] = [...currentPathRef.current];
          return newPaths;
        });
      },
      onPanResponderRelease: () => {
        // Path is finished, we don't need to do anything, state is already updated
      },
    })
  ).current;

  const handleClear = () => {
    setPaths([]);
  };

  const handleUndo = () => {
    setPaths(prev => prev.slice(0, -1));
  };

  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="fade"
      onRequestClose={onClose}
    >
      <SafeAreaView style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          
          <View style={styles.header}>
            <TouchableOpacity onPress={onClose} style={styles.iconButton}>
              <MaterialIcons name="close" size={28} color="#94A3B8" />
            </TouchableOpacity>
            
            <View style={styles.actions}>
              <TouchableOpacity onPress={handleUndo} style={styles.iconButton}>
                <MaterialIcons name="undo" size={28} color="#94A3B8" />
              </TouchableOpacity>
              <TouchableOpacity onPress={handleClear} style={styles.iconButton}>
                <MaterialIcons name="delete-outline" size={28} color="#EF4444" />
              </TouchableOpacity>
            </View>
          </View>

          <View style={styles.canvasContainer} {...panResponder.panHandlers}>
            <Svg height="100%" width="100%">
              {paths.map((pathStrArray, index) => (
                <Path
                  key={index}
                  d={pathStrArray.join(' ')}
                  stroke="#3B82F6"
                  strokeWidth={4}
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  fill="none"
                />
              ))}
            </Svg>
          </View>

        </View>
      </SafeAreaView>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.8)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  modalContent: {
    width: width * 0.9,
    height: height * 0.85,
    backgroundColor: '#1E293B',
    borderRadius: 24,
    overflow: 'hidden',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 10 },
    shadowOpacity: 0.3,
    shadowRadius: 20,
    elevation: 10,
    borderWidth: 1,
    borderColor: '#334155'
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#334155',
  },
  actions: {
    flexDirection: 'row',
    gap: 16,
  },
  iconButton: {
    padding: 8,
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
  },
  canvasContainer: {
    flex: 1,
    backgroundColor: '#0F172A',
  }
});
