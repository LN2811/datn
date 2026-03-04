export interface AppConfigs{
    baseUrl: string
    baseApiUrl: string
    folderCMSId: string
}

export const appConfigs: AppConfigs ={
    baseUrl: import.meta.env.VITE_NOTIFICATION_HOST,
    baseApiUrl: import.meta.env.VITE_API_URL,
    folderCMSId: import.meta.env.VITE_FOLDER_CMS_ID,
}