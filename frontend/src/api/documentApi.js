import client from './client';

export const uploadDocument = async (file, projectId, folderId = null, onUploadProgress) => {
  const formData = new FormData();
  formData.append('file', file);
  if (projectId) formData.append('project_id', projectId);
  if (folderId) formData.append('folder_id', folderId);

  const response = await client.post('/documents/upload', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress,
  });
  return response.data;
};
