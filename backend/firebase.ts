// Import the functions you need from the SDKs you need
import { initializeApp } from "firebase/app";
import { getFirestore } from "firebase/firestore";
import { getAnalytics } from "firebase/analytics";
import { getAuth } from "firebase/auth";

// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app'"'"'s Firebase configuration
// Replace with your actual Firebase config
const firebaseConfig = {
  apiKey: "AIzaSyAJSkvO5A9mY1wgQFfXnRo-TesownlytVU",
  authDomain: "aha-62843.firebaseapp.com",
  projectId: "aha-62843",
  storageBucket: "aha-62843.firebasestorage.app",
  messagingSenderId: "1040680730783",
  appId: "1:1040680730783:web:830c9d68331ac5fd6062aa",
  measurementId: "G-28NYH2CZX1"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);

// Initialize Firebase services
export const db = getFirestore(app);
export const auth = getAuth(app);

export default app;
