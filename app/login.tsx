import { View, Text, TextInput, StyleSheet, TouchableOpacity, Alert, Image } from 'react-native';
import { useState } from 'react';
import auth from '@react-native-firebase/auth';
import firestore from '@react-native-firebase/firestore';
import { useRouter } from 'expo-router';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const router = useRouter();

  const handleLogin = async () => {
    try {
      const userCredential = await auth().signInWithEmailAndPassword(email, password);
      const userDoc = await firestore().collection('users').doc(userCredential.user.uid).get();
      if (userDoc.exists && userDoc.data()?.grade) {
        router.replace('/subject-selection');
      } else {
        router.replace('/grade-selection');
      }
    } catch (error: any) {
      Alert.alert('Error', error.message);
    }
  };

  return (
    <View style={styles.container}>
      <Image source={require('../assets/images/sabaktutor-logo.png')} style={styles.logo} resizeMode="contain" />
      <Text style={styles.header}>SabakTutor</Text>
      <Text style={styles.title}>Welcome Back</Text>
      <Text style={styles.subtitle}>Continue your logic-first learning</Text>
      
      <TextInput
        style={styles.input}
        placeholder="Email Address"
        placeholderTextColor="#6c7b6d"
        autoCapitalize="none"
        keyboardType="email-address"
        value={email}
        onChangeText={setEmail}
      />
      <TextInput
        style={styles.input}
        placeholder="Password"
        placeholderTextColor="#6c7b6d"
        secureTextEntry
        value={password}
        onChangeText={setPassword}
      />

      <TouchableOpacity activeOpacity={0.7} style={styles.button} onPress={handleLogin}>
        <Text style={styles.buttonText}>Login</Text>
      </TouchableOpacity>

      <TouchableOpacity activeOpacity={0.7} onPress={() => router.replace('/signup')} style={styles.linkContainer}>
        <Text style={styles.linkText}>Don't have an account? Sign up</Text>
      </TouchableOpacity>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f7f9ff',
    padding: 24,
    justifyContent: 'center',
  },
  logo: {
    width: 64,
    height: 64,
    marginBottom: 16,
  },
  header: {
    fontSize: 22,
    fontWeight: '600',
    color: '#006d37',
    marginBottom: 8,
  },
  title: {
    fontSize: 32,
    fontWeight: '700',
    color: '#091d2e',
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 18,
    color: '#3d4a3e',
    marginBottom: 32,
  },
  input: {
    backgroundColor: '#ffffff',
    borderWidth: 2,
    borderColor: '#bbcbbb',
    borderRadius: 12,
    padding: 16,
    fontSize: 16,
    marginBottom: 16,
    color: '#091d2e',
  },
  button: {
    backgroundColor: '#006d37',
    paddingVertical: 16,
    borderRadius: 16,
    alignItems: 'center',
    borderBottomWidth: 4,
    borderBottomColor: '#005228',
    marginTop: 8,
  },
  buttonText: {
    color: '#ffffff',
    fontSize: 18,
    fontWeight: '700',
  },
  linkContainer: {
    marginTop: 24,
    alignItems: 'center',
  },
  linkText: {
    color: '#006d37',
    fontSize: 16,
    fontWeight: '600',
  },
});
