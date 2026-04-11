from google import genai

client = genai.Client(api_key="AIzaSyCHUr4QGVenMDLYSvVHln7oTgRPguLCChs")

response = client.models.generate_content(
    model="gemini-2.0-flash",
    contents="Hello! Reply with: API is working successfully"
)

print(response.text)