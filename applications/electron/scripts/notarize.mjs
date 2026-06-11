import { notarize } from '@electron/notarize';

export default async function notarizeMac(context) {
  if (process.platform !== 'darwin') {
    return;
  }
  const { electronPlatformName, appOutDir, packager } = context;
  if (electronPlatformName !== 'darwin') {
    return;
  }

  const appName = packager.appInfo.productFilename;
  const appPath = `${appOutDir}/${appName}.app`;
  await notarize({
    appBundleId: 'ai.arc-studio.desktop',
    appPath,
    appleApiKey: process.env.APPLE_API_KEY_PATH,
    appleApiKeyId: process.env.APPLE_API_KEY_ID,
    appleApiIssuer: process.env.APPLE_API_ISSUER_ID,
    tool: 'notarytool',
  });
}
