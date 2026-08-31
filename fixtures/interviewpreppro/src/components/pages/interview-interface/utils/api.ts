export async function getSignedUrl(): Promise<string> {
    console.log('Fetching signed URL...');
    const response = await fetch("/api/signed-url");
    console.log('Response status:', response.status);
    
    if (!response.ok) {
      const errorText = await response.text();
      console.error('API Error:', errorText);
      throw new Error(`Failed to get signed url: ${response.status} - ${errorText}`);
    }
    
    const data = await response.json();
    console.log('Signed URL received:', data);
    return data.signedUrl;
  }