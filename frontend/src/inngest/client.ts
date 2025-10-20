import { Inngest } from "inngest";

export const inngest = new Inngest({
  name: "Appia Builder",
  eventKey: process.env.INNGEST_EVENT_KEY,
});
