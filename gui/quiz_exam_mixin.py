"""Mode examen de la page de révision : tirage, minuteur, résultat et erreurs"""

from datetime import datetime

from gui.widgets import show_message
from job.interview_revision import (
    start_missing_skills_exam,
    start_offer_exam,
    start_skills_exam,
)
from job.quiz import load_active_quiz
from job.quiz_exam import (
    describe_exam_results,
    describe_exam_summary,
    format_countdown,
    get_exam_question,
    get_remaining_seconds,
    load_exam,
    load_exam_results,
    start_error_review,
    start_exam,
    stop_exam,
    summarize_exam,
)

# Mode de la page pendant un examen, à côté des modes de révision
EXAM_MODE = "exam"

# Sous cette marge, le minuteur passe à l'orange
TIMER_WARNING_SECONDS = 60


class QuizExamMixin:
    """Méthodes d'examen de QuizPage, qui fournit la carte de question et son état."""

    def start_exam(self):
        """Reprend l'examen en cours, ou en commence un sur le domaine choisi."""
        self.begin_exam(
            lambda pQuiz: start_exam(
                self.database_file,
                pQuiz,
                self.domain,
                datetime.now(),
                pSubdomain=self.subdomain,
            )
        )

    def start_offer_exam(self, pOffer):
        """Reprend l'examen en cours, ou commence l'examen blanc d'une offre."""
        self.begin_exam(
            lambda pQuiz: start_offer_exam(
                self.database_file, pQuiz, pOffer, datetime.now()
            )
        )

    def start_missing_skills_exam(self, pOffer):
        """Reprend l'examen en cours, ou commence celui des manques d'une offre."""
        self.begin_exam(
            lambda pQuiz: start_missing_skills_exam(
                self.database_file, pQuiz, pOffer, datetime.now()
            )
        )

    def start_skills_exam(self, pSkills):
        """Reprend l'examen en cours, ou commence celui des compétences prioritaires."""
        self.begin_exam(
            lambda pQuiz: start_skills_exam(
                self.database_file, pQuiz, pSkills, datetime.now()
            )
        )

    def begin_exam(self, pStart):
        """Reprend l'examen en cours ; sinon en commence un avec la fonction donnée."""
        vExam = load_exam(self.database_file)

        if not vExam or vExam["finished_at"]:
            try:
                pStart(load_active_quiz(self.database_file))

            except ValueError as vException:
                show_message(self.message_label, str(vException), "warning")
                self.message_label.show()
                return

        self.mode = EXAM_MODE
        self.show_exam_question()

    def show_exam_question(self):
        """Affiche la question en cours de l'examen, ou son résultat."""
        vQuiz = load_active_quiz(self.database_file)
        vExam = load_exam(self.database_file)

        self.current_exam = vExam

        if vExam and vExam["finished_at"]:
            vSummary = describe_exam_summary(summarize_exam(vQuiz, vExam))

            if vExam.get("offer"):
                vSummary += " " + describe_exam_results(
                    load_exam_results(self.database_file, vExam["offer"])
                )

            self.display_question(None, "Examen terminé", vSummary)
            self.stop_exam_button.setText("Fermer l'examen")
            self.review_errors_button.setText(
                f"Revoir les {len(vExam['wrong'])} erreur(s)"
            )
            self.review_errors_button.setVisible(bool(vExam["wrong"]))
            self.update_exam_timer()
            return

        self.exam_timer.start()

        vQuestion = get_exam_question(vQuiz, vExam)

        self.stop_exam_button.setText("Abandonner l'examen")
        self.update_exam_timer()
        self.display_question(
            vQuestion,
            (
                f"{vExam.get('title') or 'Examen'} · question "
                f"{vQuestion['position']} / {vQuestion['count']} · "
                f"{vQuestion['theme_label']} · {vQuestion['level']}"
                if vQuestion
                else "Examen"
            ),
            "Cette question n'existe plus : passez à la suivante.",
        )

    def review_exam_errors(self):
        """Enchaîne sur un examen limité aux questions ratées."""
        try:
            start_error_review(
                self.database_file, load_exam(self.database_file), datetime.now()
            )

        except ValueError as vException:
            show_message(self.verdict_label, str(vException), "warning")
            return

        self.show_exam_question()

    def update_exam_timer(self):
        """Affiche le temps restant de l'examen en cours, ou masque le minuteur."""
        vExam = self.current_exam

        if self.mode != EXAM_MODE or not vExam or vExam["finished_at"]:
            self.exam_timer.stop()
            self.timer_label.hide()
            return

        vRemaining = get_remaining_seconds(vExam, datetime.now())

        if vRemaining >= TIMER_WARNING_SECONDS:
            vTone = "success"
        elif vRemaining >= 0:
            vTone = "warning"
        else:
            vTone = "danger"

        show_message(self.timer_label, format_countdown(vRemaining), vTone)
        self.timer_label.show()

    def close_exam(self):
        """Abandonne ou referme l'examen, puis revient à la liste des thèmes."""
        stop_exam(self.database_file)

        self.current_exam = None
        self.update_exam_timer()

        self.mode = None
        self.question_card.hide()
        self.refresh()
