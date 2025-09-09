import fetchMock from "jest-fetch-mock"
fetchMock.enableMocks()
import "@testing-library/jest-dom"

// Mock global APP_DATA
window.APP_DATA = {
  date: "2023-10-01",
  siteLocation: "summit",
  eventUrl: "http://example.com", // Add eventUrl mock
}

// Always return valid JSON for fetch
beforeAll(() => {
  fetchMock.mockResponse(JSON.stringify({}))
})
