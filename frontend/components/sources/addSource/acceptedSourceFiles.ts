export const ACCEPTED_SOURCE_EXTENSIONS = ['.pdf', '.docx', '.txt', '.md', '.png', '.jpg', '.jpeg'] as const
export const ACCEPTED_SOURCE_FORMATS_LABEL = ACCEPTED_SOURCE_EXTENSIONS.map((ext) => ext.slice(1)).join(', ')

export const isAcceptedSourceFile = (file: File) => {
    const name = file.name.toLowerCase()
    return ACCEPTED_SOURCE_EXTENSIONS.some((ext) => name.endsWith(ext))
}
