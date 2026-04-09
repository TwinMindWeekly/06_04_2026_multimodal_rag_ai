import client from './client';

export const getProjects = async () => {
  const response = await client.get('/projects/');
  return response.data;
};

export const createProject = async (name, description = '') => {
  const response = await client.post('/projects/', { name, description });
  return response.data;
};

export const createFolder = async (projectId, name, parentId = null) => {
  const response = await client.post('/projects/folders/', {
    name,
    project_id: projectId,
    parent_id: parentId
  });
  return response.data;
};
