const express = require('express');
const mongoose = require('mongoose');
const cors = require('cors');
const Post = require('./models/Post');

const app = express();
app.use(cors());
app.use(express.json());

mongoose.connect("mongodb://127.0.0.1:27017/Caption")
  .then(() => console.log("Connected to MongoDB"))
  .catch((err) => console.error("Failed to connect", err));

async function analyzeCaption(caption) {
  const response = await fetch('http://localhost:8080/analyze', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ caption })
  });
  const data = await response.json();
  console.log("ML result:", data);
  return data;
}

app.post('/api/posts', async (req, res) => {
  const { caption } = req.body;

  if (!caption || caption.trim() === '') {
    return res.status(400).json({ error: 'Caption is required' });
  }

  try {
    const result = await analyzeCaption(caption);

    // ✅ explicitly check result.allowed === false instead of !result.allowed
    if (result.allowed === false) {
      return res.status(400).json({
        blocked: true,
        label: result.label,
        reason: result.reason,
        scores: result.scores
      });
    }

    const post = new Post({ caption });
    await post.save();
    res.status(201).json({ blocked: false, post });

  } catch (err) {
    console.error("ML service error:", err.message);
    res.status(500).json({ error: 'ML service is not running. Start app.py first.' });
  }
});

app.get('/api/posts', async (req, res) => {
  const posts = await Post.find().sort({ createdAt: -1 });
  res.json(posts);
});

app.listen(5000, () => console.log("Server running on http://localhost:5000"));
// const express = require('express');
// const mongoose = require('mongoose');
// const cors = require('cors');
// const postRoutes = require('./routes/post');

// const app = express();
// app.use(cors());
// app.use(express.json());

// mongoose.connect("mongodb://127.0.0.1:27017/Caption")
//   .then(() => console.log("Connected to MongoDB"))
//   .catch((err) => console.error("Failed to connect to MongoDB", err));

// app.use('/api/posts', postRoutes);

// app.listen(5000, () => console.log("Server running on port 5000"));