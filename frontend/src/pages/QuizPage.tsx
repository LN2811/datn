import { useEffect, useMemo, useState } from 'react';
import {
  ArrowLeft,
  CheckCircle2,
  CircleAlert,
  Loader2,
  Send,
  XCircle,
} from 'lucide-react';
import { Link, useParams } from 'react-router-dom';

import { api } from '../api/axios.ts';

import './QuizPage.css';

type QuizOption = {
  id: string;
  content: string;
  order_index?: number | null;
};

type QuizQuestion = {
  id: string;
  content: string;
  question_type?: string | null;
  explanation?: string | null;
  curriculum_module_id?: string | null;
  options: QuizOption[];
};

type QuizTarget = {
  id: string;
  project_id: string;
  title: string;
  description?: string | null;
  type?: 'assignment' | 'lesson' | string;
};

type QuizPayload = {
  assignment?: QuizTarget;
  target?: QuizTarget;
  questions: QuizQuestion[];
};

type QuizResultItem = {
  question_id: string;
  selected_option_id?: string | null;
  correct_option_id?: string | null;
  is_correct: boolean;
  explanation?: string | null;
};

type QuizSubmitResponse = {
  attempt_id: string;
  assignment_id?: string | null;
  module_id?: string | null;
  score: number;
  correct_count: number;
  total_questions: number;
  evaluation?: {
    readiness_level: 'high' | 'medium' | 'low' | string;
    title: string;
    summary: string;
    score: number;
    correct_count: number;
    total_questions: number;
    recommendations: string[];
  } | null;
  assessment_result?: {
    id: string;
    total_score?: number | null;
    readiness_level?: string | null;
    created_at?: string | null;
  } | null;
  results: QuizResultItem[];
};

const getEvaluationTone = (level?: string | null) => {
  if (level === 'high') {
    return 'high';
  }

  if (level === 'medium') {
    return 'medium';
  }

  return 'low';
};

const optionLetters = ['A', 'B', 'C', 'D', 'E', 'F'];

const getErrorMessage = (error: unknown) => {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: unknown }).response === 'object' &&
    (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail
  ) {
    const detail = (error as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return 'Không thể tải bài trắc nghiệm. Vui lòng thử lại.';
};

const sortOptions = (options: QuizOption[]) =>
  [...options].sort((left, right) => {
    const leftOrder = left.order_index ?? 999;
    const rightOrder = right.order_index ?? 999;
    return leftOrder - rightOrder;
  });

export function QuizPage() {
  const { assignmentId, moduleId } = useParams();

  const [quiz, setQuiz] = useState<QuizPayload | null>(null);
  const [selectedOptions, setSelectedOptions] = useState<Record<string, string>>({});
  const [result, setResult] = useState<QuizSubmitResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  useEffect(() => {
    let isMounted = true;

    const loadQuiz = async () => {
      if (!assignmentId && !moduleId) {
        setError('Không tìm thấy bài kiểm tra.');
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError('');
        const endpoint = moduleId
          ? `/questions/modules/${moduleId}/quiz`
          : `/questions/assignment/${assignmentId}/quiz`;
        const response = await api.get<QuizPayload>(endpoint);
        if (!isMounted) {
          return;
        }
        setQuiz(response.data);
      } catch (loadError) {
        if (!isMounted) {
          return;
        }
        setError(getErrorMessage(loadError));
      } finally {
        if (isMounted) {
          setIsLoading(false);
        }
      }
    };

    void loadQuiz();

    return () => {
      isMounted = false;
    };
  }, [assignmentId, moduleId]);

  const quizTarget = quiz?.target ?? quiz?.assignment ?? null;

  const resultByQuestion = useMemo(() => {
    const mapped: Record<string, QuizResultItem> = {};
    result?.results.forEach((item) => {
      mapped[item.question_id] = item;
    });
    return mapped;
  }, [result]);

  const answeredCount = quiz?.questions.filter((question) => selectedOptions[question.id]).length ?? 0;
  const totalQuestions = quiz?.questions.length ?? 0;

  const handleSubmit = async () => {
    if ((!assignmentId && !moduleId) || !quiz || isSubmitting || result) {
      return;
    }

    const unansweredQuestion = quiz.questions.find((question) => !selectedOptions[question.id]);
    if (unansweredQuestion) {
      setError('Vui lòng chọn đáp án cho tất cả câu hỏi trước khi nộp bài.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError('');
      const endpoint = moduleId
        ? `/questions/modules/${moduleId}/quiz/submit`
        : `/questions/assignment/${assignmentId}/quiz/submit`;
      const response = await api.post<QuizSubmitResponse>(
        endpoint,
        {
          answers: quiz.questions.map((question) => ({
            question_id: question.id,
            selected_option_id: selectedOptions[question.id],
          })),
        },
      );
      setResult(response.data);
    } catch (submitError) {
      setError(getErrorMessage(submitError));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="quiz-page">
      <section className="quiz-page__shell">
        <header className="quiz-page__header">
          <div>
            <Link className="quiz-page__back" to="/dashboard">
              <ArrowLeft size={18} />
              Dashboard
            </Link>
            <h1>{quizTarget?.title ?? 'Bài trắc nghiệm'}</h1>
          </div>

          <div className="quiz-page__status">
            <span>Đã chọn</span>
            <strong>
              {answeredCount}/{totalQuestions}
            </strong>
          </div>
        </header>

        {error ? (
          <div className="quiz-page__banner quiz-page__banner--error">
            <CircleAlert size={18} />
            <span>{error}</span>
          </div>
        ) : null}

        {result ? (
          <section className="quiz-page__result">
            <div>
              <span>Kết quả</span>
              <strong>{Math.round(result.score)}%</strong>
              <p>
                Đúng {result.correct_count}/{result.total_questions} câu.
              </p>
            </div>
            <CheckCircle2 size={28} />
          </section>
        ) : null}

        {result?.evaluation ? (
          <section
            className={`quiz-page__evaluation quiz-page__evaluation--${getEvaluationTone(
              result.evaluation.readiness_level,
            )}`}
          >
            <div className="quiz-page__evaluation-head">
              <div>
                <span>Danh gia</span>
                <h2>{result.evaluation.title}</h2>
              </div>
              <strong>{result.evaluation.readiness_level}</strong>
            </div>
            <p>{result.evaluation.summary}</p>
            {result.evaluation.recommendations.length ? (
              <ul>
                {result.evaluation.recommendations.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </section>
        ) : null}

        {isLoading ? (
          <div className="quiz-page__loading">
            <Loader2 size={22} className="quiz-page__spin" />
            <span>Đang tải câu hỏi...</span>
          </div>
        ) : null}

        {!isLoading && quiz?.questions.length === 0 ? (
          <div className="quiz-page__empty">
            <CircleAlert size={22} />
            <span>Bài này chưa có câu hỏi trắc nghiệm.</span>
          </div>
        ) : null}

        {!isLoading && quiz?.questions.length ? (
          <div className="quiz-page__questions">
            {quiz.questions.map((question, questionIndex) => {
              const questionResult = resultByQuestion[question.id];
              const sortedOptions = sortOptions(question.options);

              return (
                <section key={question.id} className="quiz-question">
                  <div className="quiz-question__top">
                    <span>Câu {questionIndex + 1}</span>
                    {questionResult ? (
                      <strong
                        className={
                          questionResult.is_correct
                            ? 'quiz-question__mark quiz-question__mark--correct'
                            : 'quiz-question__mark quiz-question__mark--wrong'
                        }
                      >
                        {questionResult.is_correct ? (
                          <CheckCircle2 size={16} />
                        ) : (
                          <XCircle size={16} />
                        )}
                        {questionResult.is_correct ? 'Đúng' : 'Sai'}
                      </strong>
                    ) : null}
                  </div>

                  <h2>{question.content}</h2>

                  {sortedOptions.length === 0 ? (
                    <div className="quiz-question__no-options">
                      Câu hỏi này chưa có đáp án lựa chọn.
                    </div>
                  ) : (
                    <div className="quiz-question__options">
                      {sortedOptions.map((option, optionIndex) => {
                        const isSelected = selectedOptions[question.id] === option.id;
                        const isCorrect = questionResult?.correct_option_id === option.id;
                        const isWrongSelection =
                          Boolean(questionResult) && isSelected && !isCorrect;

                        return (
                          <button
                            key={option.id}
                            className={[
                              'quiz-option',
                              isSelected ? 'quiz-option--selected' : '',
                              isCorrect ? 'quiz-option--correct' : '',
                              isWrongSelection ? 'quiz-option--wrong' : '',
                            ]
                              .filter(Boolean)
                              .join(' ')}
                            type="button"
                            onClick={() => {
                              if (result) {
                                return;
                              }
                              setSelectedOptions((current) => ({
                                ...current,
                                [question.id]: option.id,
                              }));
                            }}
                            disabled={Boolean(result)}
                          >
                            <span>{optionLetters[optionIndex] ?? optionIndex + 1}</span>
                            <strong>{option.content}</strong>
                          </button>
                        );
                      })}
                    </div>
                  )}

                  {questionResult?.explanation ? (
                    <p className="quiz-question__explanation">{questionResult.explanation}</p>
                  ) : null}
                </section>
              );
            })}
          </div>
        ) : null}

        {!isLoading && quiz?.questions.length ? (
          <footer className="quiz-page__footer">
            <Link
              className="quiz-page__secondary"
              to={moduleId ? `/lession/${moduleId}` : `/projects/${quizTarget?.project_id ?? ''}`}
            >
              <ArrowLeft size={18} />
              {moduleId ? 'Về bài học' : 'Về project'}
            </Link>
            <button
              className="quiz-page__submit"
              type="button"
              onClick={handleSubmit}
              disabled={isSubmitting || Boolean(result)}
            >
              {isSubmitting ? <Loader2 size={18} className="quiz-page__spin" /> : <Send size={18} />}
              {result ? 'Đã nộp bài' : isSubmitting ? 'Đang nộp...' : 'Nộp bài'}
            </button>
          </footer>
        ) : null}
      </section>
    </main>
  );
}
