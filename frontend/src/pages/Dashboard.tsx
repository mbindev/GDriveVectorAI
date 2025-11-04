import React from 'react';
import { Container, Typography, Tabs, Tab, Box } from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import SettingsIcon from '@mui/icons-material/Settings';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import SearchIcon from '@mui/icons-material/Search';
import ChatIcon from '@mui/icons-material/Chat';
import DescriptionIcon from '@mui/icons-material/Description';
import WorkIcon from '@mui/icons-material/Work';
import FolderIcon from '@mui/icons-material/Folder';
import StatisticsPage from './pages/StatisticsPage';
import SettingsPage from './pages/SettingsPage';
import IngestionPage from './pages/IngestionPage';
import SearchPage from './pages/SearchPage';
import ChatPage from './pages/ChatPage';
import DocumentsPage from './pages/DocumentsPage';
import JobsPage from './pages/JobsPage';
import FoldersPage from './pages/FoldersPage';

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
      <Typography variant="h3" component="h1" gutterBottom sx={{ mt: 3, mb: 2 }}>
        DriveVectorAI Dashboard
      </Typography>
      <Typography variant="body1" color="text.secondary" paragraph>
        AI-powered document search and management for Google Drive
      </Typography>

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs
          value={value}
          onChange={handleChange}
          aria-label="dashboard tabs"
          variant="scrollable"
          scrollButtons="auto"
        >
          <Tab icon={<DashboardIcon />} label="Overview" iconPosition="start" />
          <Tab icon={<FolderIcon />} label="Folders" iconPosition="start" />
          <Tab icon={<CloudUploadIcon />} label="Ingestion" iconPosition="start" />
          <Tab icon={<WorkIcon />} label="Jobs" iconPosition="start" />
          <Tab icon={<DescriptionIcon />} label="Documents" iconPosition="start" />
          <Tab icon={<SearchIcon />} label="Search" iconPosition="start" />
          <Tab icon={<ChatIcon />} label="Chat" iconPosition="start" />
          <Tab icon={<SettingsIcon />} label="Settings" iconPosition="start" />
        </Tabs>
      </Box>

      <TabPanel value={value} index={0}>
        <StatisticsPage />
      </TabPanel>
      <TabPanel value={value} index={1}>
        <FoldersPage />
      </TabPanel>
      <TabPanel value={value} index={2}>
        <IngestionPage />
      </TabPanel>
      <TabPanel value={value} index={3}>
        <JobsPage />
      </TabPanel>
      <TabPanel value={value} index={4}>
        <DocumentsPage />
      </TabPanel>
      <TabPanel value={value} index={5}>
        <SearchPage />
      </TabPanel>
      <TabPanel value={value} index={6}>
        <ChatPage />
      </TabPanel>
      <TabPanel value={value} index={7}>
        <SettingsPage />
      </TabPanel>
    </Container>
  );
};

export default Dashboard;
