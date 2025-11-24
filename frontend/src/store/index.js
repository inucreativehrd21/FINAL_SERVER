/**
 * Redux Store 설정
 */
import { configureStore } from '@reduxjs/toolkit'
import authReducer from './authSlice'
import codingTestReducer from './codingTestSlice'
import chatbotReducer from './chatbotSlice'

const store = configureStore({
  reducer: {
    auth: authReducer,
    codingTest: codingTestReducer,
    chatbot: chatbotReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: false,
    }),
})

export default store
