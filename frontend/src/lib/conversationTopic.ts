export const CONVERSATION_TOPICS = [
    'legal',
    'learning',
    'ai',
    'sport',
    'nature',
    'general',
    'finance',
    'health',
    'tech',
    'work',
    'science',
    'history',
    'travel',
    'politics',
    'food',
    'art',
    'career',
    'personal',
] as const

export type ConversationTopicName = (typeof CONVERSATION_TOPICS)[number]

export type ConversationTopicStyle = {
    icon: string;
    background: string;
}

const CONVERSATION_TOPIC_STYLES: Record<ConversationTopicName, ConversationTopicStyle> = {
    legal: { icon: '⚖️', background: '#efe0d4' },
    learning: { icon: '🎓', background: '#d4eadc' },
    ai: { icon: '🤖', background: '#e4e6c9' },
    sport: { icon: '⚽', background: '#cfeae6' },
    nature: { icon: '🌿', background: '#d5ebd6' },
    general: { icon: '📒', background: '#e8ecf0' },
    finance: { icon: '💰', background: '#d6e0f5' },
    health: { icon: '🩺', background: '#f3d6de' },
    tech: { icon: '💻', background: '#d6e6f4' },
    work: { icon: '💼', background: '#e6e6e6' },
    science: { icon: '🔬', background: '#d9dcf3' },
    history: { icon: '📖', background: '#dce8d8' },
    travel: { icon: '✈️', background: '#d0e6ef' },
    politics: { icon: '🏛️', background: '#edd6de' },
    food: { icon: '🍽️', background: '#f0e0cc' },
    art: { icon: '🎨', background: '#ead6ea' },
    career: { icon: '📈', background: '#d7e3f0' },
    personal: { icon: '📓', background: '#eadfd6' },
}

const DEFAULT_CONVERSATION_TOPIC_STYLE = CONVERSATION_TOPIC_STYLES.general

function isConversationTopicName(topic: string): topic is ConversationTopicName {
    return (CONVERSATION_TOPICS as readonly string[]).includes(topic)
}

export function getConversationTopicStyle(topic: string | null | undefined): ConversationTopicStyle {
    if (topic && isConversationTopicName(topic)) {
        return CONVERSATION_TOPIC_STYLES[topic]
    }

    return DEFAULT_CONVERSATION_TOPIC_STYLE
}
