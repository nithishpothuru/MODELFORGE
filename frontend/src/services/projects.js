/**
 * Projects API Service
 * Handles all backend project operations, uploads, and validation requests
 */

import { apiRequest, apiUpload } from './api';

const PREFIX = '/api/v1/projects';

/**
 * Fetch all projects
 */
export async function listProjects() {
  return apiRequest(PREFIX, { method: 'GET' });
}

/**
 * Create a new model project
 * @param {Object} projectData { title, description, framework, version }
 */
export async function createProject(projectData) {
  return apiRequest(PREFIX, {
    method: 'POST',
    body: JSON.stringify(projectData),
  });
}

/**
 * Get project by ID
 */
export async function getProject(projectId) {
  return apiRequest(`${PREFIX}/${projectId}`, { method: 'GET' });
}

/**
 * Update project metadata
 * @param {string} projectId
 * @param {Object} updateData { title, description, framework, version, status, etc. }
 */
export async function updateProject(projectId, updateData) {
  return apiRequest(`${PREFIX}/${projectId}`, {
    method: 'PUT',
    body: JSON.stringify(updateData),
  });
}

/**
 * Delete a project
 */
export async function deleteProject(projectId) {
  return apiRequest(`${PREFIX}/${projectId}`, {
    method: 'DELETE',
  });
}

/**
 * Upload a model weight or zip archive to an existing project
 * @param {string} projectId
 * @param {File} file
 * @param {Function} onProgress (percent: number) => void
 */
export async function uploadProjectFile(projectId, file, onProgress = null) {
  const formData = new FormData();
  formData.append('file', file);
  return apiUpload(`${PREFIX}/${projectId}/upload`, formData, onProgress);
}

/**
 * Quick Unpack: Convenience endpoint creating a project and unpacking archive in one step
 * @param {File} file
 * @param {string} title
 * @param {Function} onProgress
 */
export async function quickUnpack(file, title = 'Quick Model Import', onProgress = null) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('title', title);
  return apiUpload(`${PREFIX}/quick-unpack`, formData, onProgress);
}

/**
 * Trigger CI validation pipeline on an extracted project
 * @param {string} projectId
 * @param {string} [mainFile] Optional override path to main entry point
 */
export async function validateProject(projectId, mainFile = null) {
  const query = mainFile ? `?main_file=${encodeURIComponent(mainFile)}` : '';
  return apiRequest(`${PREFIX}/${projectId}/validate${query}`, {
    method: 'POST',
  });
}

/**
 * Retrieve the latest CI validation report
 * @param {string} projectId
 */
export async function getProjectValidation(projectId) {
  return apiRequest(`${PREFIX}/${projectId}/validation`, {
    method: 'GET',
  });
}

export default {
  listProjects,
  createProject,
  getProject,
  updateProject,
  deleteProject,
  uploadProjectFile,
  quickUnpack,
  validateProject,
  getProjectValidation,
};

