import { Node, mergeAttributes } from '@tiptap/core'

export interface DiaryMediaAttrs {
  placeholder: string
  type: 'image' | 'video'
  src?: string | null
  filename?: string | null
}

declare module '@tiptap/core' {
  interface Commands<ReturnType> {
    diaryMedia: {
      insertDiaryMedia: (attrs: DiaryMediaAttrs) => ReturnType
    }
  }
}

const DiaryMedia = Node.create({
  name: 'diaryMedia',
  group: 'block',
  inline: false,
  atom: true,
  selectable: true,
  draggable: false,

  addAttributes() {
    return {
      placeholder: {
        default: null,
        renderHTML: (attributes) =>
          attributes.placeholder
            ? { 'data-placeholder': attributes.placeholder }
            : {},
        parseHTML: (element: HTMLElement) => element.getAttribute('data-placeholder'),
      },
      type: {
        default: 'image',
        renderHTML: (attributes) =>
          attributes.type ? { 'data-media-type': attributes.type } : {},
        parseHTML: (element: HTMLElement) =>
          (element.getAttribute('data-media-type') as 'image' | 'video') ??
          (element.querySelector('video') ? 'video' : 'image'),
      },
      src: {
        default: null,
        renderHTML: (attributes) =>
          attributes.src ? { 'data-preview-src': attributes.src } : {},
        parseHTML: (element: HTMLElement) => {
          const media = element.querySelector('img,video') as HTMLImageElement | HTMLVideoElement | null
          return media?.getAttribute('src') ?? null
        },
      },
      filename: {
        default: null,
        renderHTML: (attributes) =>
          attributes.filename ? { 'data-filename': attributes.filename } : {},
        parseHTML: (element: HTMLElement) =>
          element.getAttribute('data-filename') ?? element.querySelector('figcaption')?.textContent ?? null,
      },
    }
  },

  parseHTML() {
    return [{ tag: 'figure[data-placeholder]' }]
  },

  renderHTML({ HTMLAttributes }) {
    const { placeholder, type, src, filename } = HTMLAttributes as DiaryMediaAttrs
    const baseAttrs = mergeAttributes(HTMLAttributes, {
      'data-placeholder': placeholder,
      'data-media-type': type,
      class: 'editor-media-block',
      contenteditable: 'false',
    })

    const mediaChild =
      type === 'video'
        ? ['video', mergeAttributes({ src: src ?? '', controls: '', preload: 'metadata' })]
        : ['img', mergeAttributes({ src: src ?? '', alt: filename ?? '' })]

    const children: any[] = [mediaChild]
    if (filename) {
      children.push(['figcaption', filename])
    }

    return ['figure', baseAttrs, ...children]
  },

  addCommands() {
    return {
      insertDiaryMedia:
        (attrs: DiaryMediaAttrs) =>
        ({ commands }) =>
          commands.insertContent({
            type: this.name,
            attrs,
          }),
    }
  },

  addNodeView() {
    return ({ node }) => {
      const render = (attrs: DiaryMediaAttrs) => {
        figure.replaceChildren()

        const placeholderValue = attrs.placeholder ?? figure.dataset.placeholder ?? ''
        const typeValue = attrs.type ?? (figure.dataset.mediaType as DiaryMediaAttrs['type']) ?? 'image'
        const previousSrc = figure.dataset.previewSrc ?? ''
        const srcValue = attrs.src ?? previousSrc
        const filenameValue = attrs.filename ?? figure.dataset.filename ?? ''

        figure.dataset.placeholder = placeholderValue
        figure.dataset.mediaType = typeValue
        figure.dataset.previewSrc = srcValue
        figure.dataset.filename = filenameValue
        figure.setAttribute('data-placeholder', placeholderValue)
        figure.setAttribute('data-media-type', typeValue)

        if (typeValue === 'video') {
          const video = document.createElement('video')
          video.controls = true
          video.preload = 'metadata'
          if (srcValue) {
            video.src = srcValue
          }
          video.classList.add('editor-media-asset')
          figure.append(video)
        } else {
          const img = document.createElement('img')
          if (srcValue) {
            img.src = srcValue
          }
          img.alt = filenameValue || ''
          img.classList.add('editor-media-asset')
          figure.append(img)
        }

        if (filenameValue) {
          const caption = document.createElement('figcaption')
          caption.textContent = filenameValue
          figure.append(caption)
        }
      }

      const figure = document.createElement('figure')
      figure.classList.add('editor-media-block')
      figure.contentEditable = 'false'

      render(node.attrs as DiaryMediaAttrs)

      return {
        dom: figure,
        update: (updatedNode) => {
          if (updatedNode.type.name !== this.name) {
            return false
          }
          render(updatedNode.attrs as DiaryMediaAttrs)
          return true
        },
      }
    }
  },
})

export default DiaryMedia
