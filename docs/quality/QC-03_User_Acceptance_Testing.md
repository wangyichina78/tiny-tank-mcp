# QC-03 User Acceptance Testing (UAT)

**Question it answers:** does this do what the business user actually needs?

Regression and security tests prove the system works as built. UAT proves it was built right for its users. Business users run it, in their own words, on realistic scenarios, and they sign it off. A system can pass every automated test and still fail UAT, because the requirement itself was misunderstood.

## 1. When UAT is needed

- Before the first release.
- Before any release that changes behaviour a user can see: new features, changed answers, new tools.
- **Not** for internal changes with no visible effect, as long as regression testing is green. Record the decision to skip UAT in the change log (QA-01).

## 2. Preparing UAT, step by step

1. **Pick the testers:** two or three real users from the business area, not developers.
2. **Write scenarios from their work,** not from the feature list. A good scenario is a real question or task: "Which tanks at Site B need attention this week, and why?"
3. **Write acceptance criteria before testing starts,** as a list of facts the answer must contain and things it must not do. Agree them with the owner. Writing them after the results are in invites moving the goalposts.
4. **Include unhappy paths:** wrong input, missing data, a question outside scope, a user insisting on something false.
5. **Prepare the test environment and data,** separate from production. Use known data, so the right answer is known in advance. *Example:* the MCP test data had planted problems (an overdue inspection, a rising level in an out-of-service tank), so testers could check whether the agent found them.
6. **Decide the pass threshold.** For deterministic systems: every scenario passes. For AI systems: see section 4.

## 3. Scenario template

```
ID:           UAT-0X
Scenario:     <the user's real question or task, in their words>
Setup:        <data, permissions, starting state>
Must contain: <facts, values, citations the answer must include>
Must not:     <invent values, take actions, overreach — e.g. call a tank "safe to fill">
Runs:         <1 for deterministic systems; 3 or more for AI systems>
Result:       <pass / fail per run, with the actual answer saved>
Tester:       <name>        Date: <YYYY-MM-DD>
```

## 4. UAT for AI and agent systems

AI answers vary from run to run, so a single pass proves little.

- **Run each scenario at least 3 times,** each in a fresh conversation.
- **Report results as rates** ("ok_basic 3/3, multi_tank 2/3"), not as pass/fail.
- **Two out of three is a finding, not noise.** Log it in QA-04, and decide whether the fix belongs in the tool, the agent's instructions or the test.
- **Before counting a failure against the system, read the actual answer.** The acceptance criterion may be what's wrong. *Example:* one test case asked the agent to confirm a status "without looking it up", then failed it for not looking it up. The agent's refusal was the correct behaviour.
- **Test on the platform users will actually use.** Different agent platforms decide differently about when to call tools.
- **Where a second model grades answers, give it one clear failure condition.** A loosely worded grading rule gave different verdicts on identical answers.

## 5. Sign-off

UAT ends with a written decision by the owner, based on the testers' results:

```
UAT sign-off
Version tested:   <commit/tag>              Environment: <name>
Scenarios:        <passed>/<total>  (AI: rates per scenario attached)
Open findings:    <QA-04 IDs, with the owner's decision on each: fix before release / accept / defer>
Decision:         Accepted | Accepted with conditions: <...> | Rejected
Owner:            <name>      Date: <YYYY-MM-DD>
Testers:          <names>
```

A rejected UAT goes back to development, and the next attempt reruns all scenarios, not just the failed ones.
