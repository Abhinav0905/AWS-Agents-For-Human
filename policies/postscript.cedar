// Postscript interruption policy.
//
// Evaluated by Strands' vended CedarAuthorization intervention before every tool call.
//   principal  Agent::"runner"        the background clerk
//   action     Action::"<tool name>"  one Cedar action per tool
//   resource   Resource::"agent"      fixed by the Strands integration
//   context.input                     the tool call arguments
//   context.session                   task facts injected by the governor:
//                                     task_id, heir_conflict, human_approved, approval_types
// Cedar denies by default. These three permits are the whole policy.

// Clerical work never interrupts the executor: reading requirements, checking status,
// following up, drafting, updating the ledger, and asking the executor a question.
// D5: once an heir objects, the only allowed moves on that task are to log, to block it,
//     and to ask the executor.
permit (
  principal == Agent::"runner",
  action in [
    Action::"list_institutions", Action::"get_requirements", Action::"check_status",
    Action::"send_follow_up", Action::"get_inbox", Action::"get_playbook", Action::"render_letter",
    Action::"ledger_get_task", Action::"ledger_update_task", Action::"schedule_follow_up",
    Action::"notes_log", Action::"decisions_request"
  ],
  resource
)
unless {
  context.session.heir_conflict &&
  !(action in [Action::"decisions_request", Action::"notes_log", Action::"ledger_get_task", Action::"ledger_update_task"])
};

// Sending a packet is clerical only when it holds copies and needs no signature.
// D2: includes_original == true means a certified original leaves the executor's hands.
// D3: signature_kind other than "none" means the executor must sign, notarize or appear.
// A packet that does not declare both fields is not clerical.
permit (
  principal == Agent::"runner",
  action in [Action::"submit_notification", Action::"submit_document"],
  resource
)
unless {
  context.session.heir_conflict ||
  !(context.input has includes_original) ||
  !(context.input has signature_kind) ||
  context.input.includes_original == true ||
  context.input.signature_kind != "none"
};

// D1 pay, D4 close_account / elect_option, and D2/D3 packets: only with a live approval
// on this task. The approval token is minted by the executor in the inbox and is single use;
// the governor consumes it after the permitted call.
permit (
  principal == Agent::"runner",
  action in [
    Action::"pay", Action::"close_account", Action::"elect_option",
    Action::"submit_notification", Action::"submit_document"
  ],
  resource
)
when {
  context.session.human_approved == true &&
  context.session.heir_conflict == false
};
