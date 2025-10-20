import { Inngest } from "inngest";

export const inngest = new Inngest({
  id: "appia-builder",
  eventKey: process.env.INNGEST_EVENT_KEY,
});
