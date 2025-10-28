import React from 'react';
import { Container, Typography, Box, TextField, Button, Paper, List, ListItem, ListItemText, Chip, Switch, FormControlLabel, Select, MenuItem, FormControl, InputLabel } from '@mui/material';
import axios from 'axios';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface Source {
  drive_file_id: string;
  file_name: string;
  similarity_score: number;
}

const ChatPage: React.FC = () => {
  const [messages, setMessages] = React.useState<Message[]>([]);
  const [currentMessage, setCurrentMessage] = React.useState('');
  const [loading, setLoading] = React.useState(false);
  const [enableRAG, setEnableRAG] = React.useState(true);
  const [selectedModel, setSelectedModel] = React.useState('gemini-1.5-pro');
  const [availableModels, setAvailableModels] = React.useState<string[]>([]);

  React.useEffect(() => {
    // Fetch available models
    axios.get('/api/llm/models').then(response => {
      setAvailableModels(response.data.models);
    });
  }, []);

  const handleSendMessage = async () => {
    if (!currentMessage.trim()) return;

    const userMessage: Message = {
      role: 'user',
      content: currentMessage,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMessage]);
    setCurrentMessage('');
    setLoading(true);

    try {
      const history = messages.slice(-10).map(msg => ({
        role: msg.role,
        content: msg.content
      }));

      const response = await axios.post('/api/llm/chat', {
        message: userMessage.content,
        history: history,
        enable_rag: enableRAG
      });

      const assistantMessage: Message = {
        role: 'assistant',
        content: response.data.response,
        timestamp: new Date()
      };

      setMessages(prev => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Chat error:', error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Container maxWidth="lg">
      <Typography variant="h4" component="h1" gutterBottom>
        AI Chat Assistant
      </Typography>

      <Box sx={{ mb: 3, display: 'flex', gap: 2, alignItems: 'center' }}>
        <FormControlLabel
          control={
            <Switch
              checked={enableRAG}
              onChange={(e) => setEnableRAG(e.target.checked)}
            />
          }
          label="Enable RAG (Retrieval-Augmented Generation)"
        />

        <FormControl size="small" sx={{ minWidth: 200 }}>
          <InputLabel>Model</InputLabel>
          <Select
            value={selectedModel}
            label="Model"
            onChange={(e) => setSelectedModel(e.target.value)}
          >
            {availableModels.map((model) => (
              <MenuItem key={model} value={model}>
                {model}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <Paper sx={{ height: 400, overflow: 'auto', p: 2, mb: 2 }}>
        {messages.length === 0 && (
          <Typography variant="body2" color="text.secondary" sx={{ textAlign: 'center', mt: 10 }}>
            Start a conversation by typing a message below.
          </Typography>
        )}

        <List>
          {messages.map((message, index) => (
            <ListItem key={index} sx={{ flexDirection: 'column', alignItems: 'flex-start' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <Chip
                  label={message.role === 'user' ? 'You' : 'Assistant'}
                  color={message.role === 'user' ? 'primary' : 'secondary'}
                  size="small"
                />
                <Typography variant="caption" color="text.secondary">
                  {message.timestamp.toLocaleTimeString()}
                </Typography>
              </Box>
              <Typography variant="body1" sx={{ whiteSpace: 'pre-wrap' }}>
                {message.content}
              </Typography>
            </ListItem>
          ))}
        </List>
      </Paper>

      <Box sx={{ display: 'flex', gap: 1 }}>
        <TextField
          fullWidth
          placeholder="Type your message..."
          value={currentMessage}
          onChange={(e) => setCurrentMessage(e.target.value)}
          onKeyPress={(e) => e.key === 'Enter' && !e.shiftKey && handleSendMessage()}
          disabled={loading}
          multiline
          maxRows={4}
        />
        <Button
          variant="contained"
          onClick={handleSendMessage}
          disabled={loading || !currentMessage.trim()}
          size="large"
        >
          {loading ? 'Sending...' : 'Send'}
        </Button>
      </Box>
    </Container>
  );
};

export default ChatPage;
