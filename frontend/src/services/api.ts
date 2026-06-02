import axios from 'axios';
import { Document, UploadResponse, ExtractionTriggerResponse, HealthResponse } from '../types';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const apiService = {
  async uploadDocument(file: File): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await apiClient.post<UploadResponse>('/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  async triggerExtraction(documentId: string): Promise<ExtractionTriggerResponse> {
    const response = await apiClient.post<ExtractionTriggerResponse>(`/extract/${documentId}`);
    return response.data;
  },

  async getDocument(documentId: string): Promise<Document> {
    const response = await apiClient.get<Document>(`/document/${documentId}`);
    return response.data;
  },

  async listDocuments(): Promise<Document[]> {
    const response = await apiClient.get<Document[]>('/document');
    return response.data;
  },

  async deleteDocument(documentId: string): Promise<void> {
    await apiClient.delete(`/document/${documentId}`);
  },

  async checkHealth(): Promise<HealthResponse> {
    const response = await apiClient.get<HealthResponse>('/health');
    return response.data;
  }
};
