import React from 'react';
import { Container, Typography, Tabs, Tab, Box } from '@mui/material';
import SettingsPage from './pages/SettingsPage';
import IngestionPage from './pages/IngestionPage';
import SearchPage from './pages/SearchPage';
import ChatPage from './pages/ChatPage';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`simple-tabpanel-${index}`}
      aria-labelledby={`simple-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Dashboard: React.FC = () => {
  const [value, setValue] = React.useState(0);

  const handleChange = (event: React.SyntheticEvent, newValue: number) => {
    setValue(newValue);
  };

  return (
    <Container maxWidth="xl">
      <Typography variant="h3" component="h1" gutterBottom sx={{ mt: 3 }}>
        DriveVectorAI Dashboard
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={value} onChange={handleChange} aria-label="dashboard tabs">
          <Tab label="Settings" />
          <Tab label="Ingestion" />
          <Tab label="Search" />
          <Tab label="Chat" />
        </Tabs>
      </Box>

      <TabPanel value={value} index={0}>
        <SettingsPage />
      </TabPanel>
      <TabPanel value={value} index={1}>
        <IngestionPage />
      </TabPanel>
      <TabPanel value={value} index={2}>
        <SearchPage />
      </TabPanel>
      <TabPanel value={value} index={3}>
        <ChatPage />
      </TabPanel>
    </Container>
  );
};

export default Dashboard;
