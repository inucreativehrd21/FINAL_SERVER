/**
 * Coding Test State Management
 */
import { createSlice } from '@reduxjs/toolkit'

const initialState = {
  problems: [],
  currentProblem: null,
  userCode: '',
  executionResult: null,
  hints: [],
  bookmarks: [],
  loading: false,
  error: null,
}

const codingTestSlice = createSlice({
  name: 'codingTest',
  initialState,
  reducers: {
    setProblems: (state, action) => {
      state.problems = action.payload
    },
    setCurrentProblem: (state, action) => {
      state.currentProblem = action.payload
      state.userCode = ''
      state.executionResult = null
      state.hints = []
    },
    setUserCode: (state, action) => {
      state.userCode = action.payload
    },
    setExecutionResult: (state, action) => {
      state.executionResult = action.payload
    },
    addHint: (state, action) => {
      state.hints.push(action.payload)
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
  },
})

export const {
  setProblems,
  setCurrentProblem,
  setUserCode,
  setExecutionResult,
  addHint,
  setBookmarks,
  addBookmark,
  removeBookmark,
  setLoading,
  setError,
} = codingTestSlice.actions

export default codingTestSlice.reducer
