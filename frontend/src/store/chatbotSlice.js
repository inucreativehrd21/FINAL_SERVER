/**
 * Chatbot State Management
 */
import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  messages: [],
  bookmarks: [],
  loading: false,
  error: null,
}

const chatbotSlice = createSlice({
  name: 'chatbot',
  initialState,
  reducers: {
    addMessage: (state, action) => {
      state.messages.push(action.payload)
    },
    setMessages: (state, action) => {
      state.messages = action.payload
    },
    updateMessage: (state, action) => {
      const { id, updates } = action.payload
      const message = state.messages.find((m) => m.id === id)
      if (message) {
        Object.assign(message, updates)
      }
    },
    setBookmarks: (state, action) => {
      state.bookmarks = action.payload
    },
    addBookmark: (state, action) => {
      state.bookmarks.push(action.payload)
    },
    removeBookmark: (state, action) => {
      state.bookmarks = state.bookmarks.filter((b) => b.id !== action.payload)
    },
    setLoading: (state, action) => {
      state.loading = action.payload
    },
    setError: (state, action) => {
      state.error = action.payload
    },
    clearMessages: (state) => {
      state.messages = []
    },
  },
})

export const {
  addMessage,
  setMessages,
  updateMessage,
  setBookmarks,
  addBookmark,
  removeBookmark,
  setLoading,
  setError,
  clearMessages,
} = chatbotSlice.actions

export default chatbotSlice.reducer
