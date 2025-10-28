import React from 'react';
import { Container, Typography, TextField, Button, Box, Alert } from '@mui/material';
import axios from 'axios';

const SettingsPage: React.FC = () => {
  const [settings, setSettings] = React.useState({
    googleProjectId: '',
    driveFolderId: '',
    dbSecretId: '',
    gcsBucketName: ''
  });
  const [message, setMessage] = React.useState<{ type: 'success' | 'error'; text: string } | null>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSettings({
      ...settings,
      [e.target.name]: e.target.value
    });
  };

  const handleSave = async () => {
    try {
      await axios.post('/api/settings', settings);
      setMessage({ type: 'success', text: 'Settings saved successfully!' });
    } catch (error) {
      setMessage({ type: 'error', text: 'Failed to save settings. Please try again.' });
    }
  };

  return (
    <Container maxWidth="md">
      <Typography variant="h4" component="h1" gutterBottom>
        Settings
      </Typography>

      {message && (
        <Alert severity={message.type} sx={{ mb: 2 }}>
          {message.text}
        </Alert>
      )}

      <Box component="form" sx={{ mt: 3 }}>
        <TextField
          fullWidth
          label="Google Project ID"
          name="googleProjectId"
          value={settings.googleProjectId}
          onChange={handleChange}
          margin="normal"
          required
        />
        <TextField
          fullWidth
          label="Drive Folder ID"
          name="driveFolderId"
          value={settings.driveFolderId}
          onChange={handleChange}
          margin="normal"
          required
        />
        <TextField
          fullWidth
          label="Database Secret ID"
          name="dbSecretId"
          value={settings.dbSecretId}
          onChange={handleChange}
          margin="normal"
          required
        />
        <TextField
          fullWidth
          label="GCS Bucket Name"
          name="gcsBucketName"
          value={settings.gcsBucketName}
          onChange={handleChange}
          margin="normal"
        />
        <Button
          variant="contained"
          onClick={handleSave}
          sx={{ mt: 3 }}
          size="large"
        >
          Save Settings
        </Button>
      </Box>
    </Container>
  );
};

export default SettingsPage;
