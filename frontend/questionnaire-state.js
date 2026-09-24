(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  root.ToolGuideQuestionnaireState = api;
}(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  function clone(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function defaultSeed() {
    if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
    return `session-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  }

  function defaultConstraints() {
    return {
      requires_offline: false,
      requires_free_plan: false,
      requires_open_source: false,
      allows_online_preparation: false,
    };
  }

  function createQuestionnaireState(seedFactory = defaultSeed) {
    return {
      stage: null,
      domain: null,
      sessionSeed: null,
      askedQuestionIds: [],
      answers: [],
      constraints: defaultConstraints(),

      setConstraints(constraints) {
        this.constraints = { ...defaultConstraints(), ...clone(constraints) };
      },

      adoptRequest(request) {
        if (request.stage !== this.stage || request.domain !== this.domain || request.session_seed !== this.sessionSeed) {
          throw new Error('scenario must preserve the selected path');
        }
        this.askedQuestionIds = clone(request.asked_question_ids);
        this.answers = clone(request.answers);
        this.setConstraints(request.constraints || {});
      },

      selectStage(stage) {
        this.constraints = defaultConstraints();
        this.stage = stage;
        this.domain = null;
        this.sessionSeed = null;
        this.askedQuestionIds = [];
        this.answers = [];
      },

      selectDomain(domain) {
        this.constraints = defaultConstraints();
        if (!this.stage) throw new Error('select a stage before a domain');
        this.domain = domain;
        this.sessionSeed = seedFactory();
        this.askedQuestionIds = [];
        this.answers = [];
      },

      recordAnswer(answer) {
        if (!answer?.question_id) throw new Error('answer requires question_id');
        if (this.askedQuestionIds.includes(answer.question_id)) {
          throw new Error(`question already answered: ${answer.question_id}`);
        }
        this.askedQuestionIds.push(answer.question_id);
        this.answers.push(clone(answer));
      },

      replaceAnswer(answer) {
        const index = this.askedQuestionIds.indexOf(answer?.question_id);
        if (index < 0) throw new Error('cannot replace an unanswered question');
        this.answers[index] = clone(answer);
      },

      toRequest(language) {
        if (!this.stage || !this.domain || !this.sessionSeed) {
          throw new Error('questionnaire path is incomplete');
        }
        return clone({
          language,
          stage: this.stage,
          domain: this.domain,
          session_seed: this.sessionSeed,
          constraints: this.constraints,
          asked_question_ids: this.askedQuestionIds,
          answers: this.answers,
        });
      },

      restart() {
        this.constraints = defaultConstraints();
        this.stage = null;
        this.domain = null;
        this.sessionSeed = null;
        this.askedQuestionIds = [];
        this.answers = [];
      },
    };
  }

  return { createQuestionnaireState };
}));
