import { ref } from 'vue'

interface UseApiRequestOptions<TData, TArgs extends unknown[]> {
  immediate?: boolean
  initialData?: TData | null
  defaultArgs?: TArgs
}

export function useApiRequest<TData, TArgs extends unknown[]>(
  fn: (...args: TArgs) => Promise<TData>,
  options: UseApiRequestOptions<TData, TArgs> = {}
) {
  const loading = ref(false)
  const error = ref<Error | null>(null)
  const data = ref<TData | null>(options.initialData ?? null)
  let lastArgs: TArgs | null = null
  let requestToken = 0

  const execute = async (...args: TArgs) => {
    loading.value = true
    error.value = null
    requestToken += 1
    const currentToken = requestToken
    lastArgs = args

    try {
      const result = await fn(...args)
      if (currentToken === requestToken) {
        data.value = result
      }
      return result
    } catch (err) {
      if (currentToken === requestToken) {
        error.value = err instanceof Error ? err : new Error('未知错误')
      }
      throw err
    } finally {
      if (currentToken === requestToken) {
        loading.value = false
      }
    }
  }

  const refresh = async () => {
    if (!lastArgs) {
      return null
    }
    return execute(...lastArgs)
  }

  const reset = () => {
    requestToken += 1
    loading.value = false
    error.value = null
    data.value = options.initialData ?? null
    lastArgs = null
  }

  if (options.immediate && options.defaultArgs && typeof window !== 'undefined') {
    void execute(...options.defaultArgs)
  }

  return {
    loading,
    error,
    data,
    execute,
    refresh,
    reset,
  }
}
