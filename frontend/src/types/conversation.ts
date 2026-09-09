export type Conversation = {
    id: string;
    createdAt: string;
    updatedAt: string;
    userId: string;
    sourceCount: number;
    title: string;
    topic: string | null;
    documentsSummary: string | null;
}
