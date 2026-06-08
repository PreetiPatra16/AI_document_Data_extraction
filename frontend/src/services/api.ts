import axios, { AxiosError } from 'axios';
import {
  ApiErrorBody,
  AppError,
  DocumentRecord,
  ExtractionTriggerResponse,
  HealthResponse,
  JobRecord,
  ReadinessResponse,
  UploadResponse,
} from '../types';

export const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1';

const apiClient = axios.create({ baseURL: API_BASE_URL });

export function parseApiError(error: unknown): AppError {
  const axiosError = error as AxiosError<{ error?: ApiErrorBody }>;
  const body = axiosError.response?.data?.error;
  return {
    status: axiosError.response?.status ?? null,
    code: body?.code ?? (axiosError.code === 'ERR_NETWORK' ? 'network_error' : 'unknown_error'),
    message: body?.message ?? (axiosError.code === 'ERR_NETWORK'
      ? 'Cannot connect to the local extraction service.'
      : 'An unexpected request error occurred.'),
    details: body?.details ?? {},
    requestId: body?.request_id ?? axiosError.response?.headers?.['x-request-id'] ?? null,
  };
}

export const apiService = {
  async uploadDocument(file: File, onProgress?: (progress: number) => void): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<UploadResponse>('/upload', formData, {
      onUploadProgress: (event) => {
        if (event.total) onProgress?.(Math.round((event.loaded / event.total) * 100));
      },
    });
    return response.data;
  },
  async triggerExtraction(documentId: string): Promise<ExtractionTriggerResponse> {
    return (await apiClient.post<ExtractionTriggerResponse>(`/extract/${documentId}`)).data;
  },
  async getJob(jobId: string): Promise<JobRecord> {
    return (await apiClient.get<JobRecord>(`/jobs/${jobId}`)).data;
  },
  async getDocument(documentId: string): Promise<DocumentRecord> {
    return (await apiClient.get<DocumentRecord>(`/document/${documentId}`)).data;
  },
  async listDocuments(): Promise<DocumentRecord[]> {
    return (await apiClient.get<DocumentRecord[]>('/document')).data;
  },
  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/document/${documentId}`);
  },
  async checkHealth(): Promise<HealthResponse> {
    return (await apiClient.get<HealthResponse>('/health')).data;
  },
  async checkReadiness(): Promise<ReadinessResponse> {
    return (await apiClient.get<ReadinessResponse>('/health/ready')).data;
  },
};
