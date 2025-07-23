"use client";
import { useState, useEffect } from "react";

export default function Home() {
  const [message, setMessage] = useState("");

  useEffect(() => {
    fetch("http://localhost:8000/")
      .then(res => res.json())
      .then(data => setMessage(data.msg))
      .catch(err => console.error("Failed to fetch:", err));
  }, []);

  return (
    <div>
      <h1>DeepCuts</h1>
      <p>{message || "Loading..."}</p>
    </div>
  );
}