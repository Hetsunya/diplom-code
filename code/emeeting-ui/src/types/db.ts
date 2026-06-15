// src/types/db.ts

export type SessionType = 'interview' | 'meeting' | 'assessment' | 'other';
export type LocationType = 'online' | 'offline' | 'hybrid';
export type DataSource = 'video' | 'audio' | 'multimodal';
// src/types/db.ts


export interface AuthUser {
  authUserId: number;
  email: string;
  passwordHash: string;
  isActive: boolean;
  createdAt: string;
  lastLogin?: string | null;
}

export interface AuthRole {
  authRoleId: number;
  code: string;
  description?: string;
}

export interface AuthUserRole {
  authUserId: number;
  authRoleId: number;
}

export interface Person {
  personId: number;
  lastName: string;
  firstName: string;
  middleName?: string;
  createdAt: string;
}

export interface Profile {
  profileId: number;
  personId: number;
  authUserId?: number | null;
  employeeNumber?: string;
  position?: string;
  department?: string;
  hiringDate?: string;
  resumeUrl?: string;
  isActive: boolean;
}

export interface CreateSessionDTO {
  title: string;
  description?: string;
  startDatetime: string; // ISO string
  endDatetime?: string; // ISO string
  sessionType: SessionType;
  locationType?: LocationType;
  physicalLocation?: string;
  analysisConfigId?: number;
}

export interface Session extends CreateSessionDTO {
  sessionId: number;
  createdBy?: number;
  createdAt: string;
  updatedAt: string;
  analysisConfigJson?: unknown;
}

export type AnalysisModules = {
  audio?: boolean;
  text?: boolean;
  face?: boolean;
  report?: boolean;
};

export interface UserAnalysisConfig {
  analysisConfigId: number;
  authUserId: number;
  name: string;
  modulesJson: AnalysisModules;
  isDefault: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface SessionParticipant {
  sessionParticipantId: number;
  sessionId: number;
  profileId: number;
  sessionRoleId?: number;
  joinDatetime?: string;
  leaveDatetime?: string;
  isActive: boolean;
  comment?: string;
}

export interface SessionRole {
  sessionRoleId: number;
  code: string;
  description?: string;
}

export interface VideoStream {
  videoStreamId: number;
  sessionId: number;
  filePath: string;
  frameRate?: number;
  resolution?: string;
  durationSec?: number;
  codec?: string;
  recordedBy?: number;
  uploadedAt: string;
}

export interface AudioStream {
  audioStreamId: number;
  sessionId: number;
  filePath: string;
  sampleRate?: number;
  channels?: number;
  durationSec?: number;
  codec?: string;
  recordedBy?: number;
  uploadedAt: string;
}

export interface EmotionCategory {
  emotionCategoryId: number;
  name: string;
  description?: string;
}

export interface EmotionType {
  emotionTypeId: number;
  emotionCategoryId: number;
  name: string;
  detectionThreshold?: number;
  description?: string;
}

export interface EmotionAnalysisConfig {
  configId: number;
  name: string;
  description?: string;
  modelName: string;
  analysisIntervalSec?: number;
  minConfidence?: number;
  sensitivity?: number;
  defaultSource: DataSource;
  isActive: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ConfigEmotionType {
  configId: number;
  emotionTypeId: number;
}

export interface EmotionRecord {
  emotionRecordId: number;
  sessionParticipantId: number;
  emotionTypeId: number;
  configId: number;
  videoStreamId?: number;
  audioStreamId?: number;
  timeStartSec?: number;
  timeEndSec?: number;
  intensity?: number;
  confidence?: number;
  dataSource: DataSource;
  createdAt: string;
}

export interface ReportType {
  reportTypeId: number;
  code: string;
  description?: string;
}

export interface Report {
  reportId: number;
  sessionId: number;
  reportTypeId?: number;
  version: number;
  createdAt: string;
  updatedAt: string;
  summaryJson?: unknown;
  participantsJson?: unknown;
  dashboardJson?: unknown;
}
