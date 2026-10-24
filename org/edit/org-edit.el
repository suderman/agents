;;; org-edit.el --- Let Org make agents' state and date changes  -*- lexical-binding: t; -*-

;; Batch entry points, run through the org-edit wrapper:
;;   org-edit-todo      FILE HEADING STATE
;;   org-edit-schedule  FILE HEADING WHEN
;;   org-edit-deadline  FILE HEADING WHEN
;;   org-edit-date      WHEN
;;
;; Agents write content as text. States and dates go through Org, so CLOSED,
;; repeaters, LOGBOOK entries, and weekdays come out as Emacs makes them.
;; HEADING is a title without keyword, priority, or tags, or id:UUID.
;; Loading org-dispatch.el shares its TODO keywords and settings.

(require 'org-dispatch)

;; Jon's Emacs logs a repeating task's completion; the dispatcher keeps its own run log.
(setq org-log-repeat 'time
      backtrace-on-error-noninteractive nil)

(defconst org-edit--cookie-re "\\`\\(?:[.+]?\\+\\|--?\\)[0-9]+[hdwmy]\\'"
  "A repeater or warning, such as +1w, .+1d, or -2d.")

(defconst org-edit--date-re
  (concat "\\`\\(?:[0-9]\\{4\\}-[0-9]\\{2\\}-[0-9]\\{2\\}\\|[+-][0-9]+[dwmy]\\|today\\|tomorrow"
          "\\|mon\\(?:day\\)?\\|tue\\(?:sday\\)?\\|wed\\(?:nesday\\)?\\|thu\\(?:rsday\\)?"
          "\\|fri\\(?:day\\)?\\|sat\\(?:urday\\)?\\|sun\\(?:day\\)?\\)\\'")
  "Date words org-edit accepts. `org-read-date' reads anything else as today.")

(defconst org-edit--time-re
  "\\`\\([0-9]\\{1,2\\}:[0-5][0-9]\\)\\(?:-\\([0-9]\\{1,2\\}:[0-5][0-9]\\)\\)?\\'")

(defun org-edit--args (n usage)
  "Pop N command-line arguments, or fail with USAGE."
  (let ((args (seq-take command-line-args-left n)))
    (setq command-line-args-left nil)
    (unless (and (= (length args) n) (not (member "" args)))
      (error "usage: org-edit %s" usage))
    args))

(defun org-edit--stamp (when)
  "The active timestamp for WHEN: one date word, an optional time or
range, and optional repeater and warning cookies."
  (let (date time end cookies)
    (dolist (word (split-string (downcase when)))
      (cond
       ;; +3d is the date until there is one, then a repeater.
       ((and date (string-match-p org-edit--cookie-re word)) (push word cookies))
       ((string-match org-edit--time-re word)
        (when time (error "two times in %S" when))
        (setq time (match-string 1 word) end (match-string 2 word)))
       ((string-match-p org-edit--date-re word)
        (when date (error "two dates in %S" when))
        (setq date word))
       (t (error "not a date, time, or cookie: %S (use YYYY-MM-DD, +3d, fri, 14:00, +1w)" word))))
    (unless date (error "no date in %S" when))
    (let ((day (org-read-date nil t (if (equal date "tomorrow") "+1d" date)))
          (pad (lambda (hm) (if (= (length hm) 4) (concat "0" hm) hm))))
      (format "<%s%s%s%s>"
              (format-time-string "%F %a" day)
              (if time (concat " " (funcall pad time)) "")
              (if end (concat "-" (funcall pad end)) "")
              (mapconcat (lambda (c) (concat " " c)) (nreverse cookies) "")))))

(defun org-edit--headings (heading)
  "Positions of the headings HEADING names in the current buffer."
  (if (string-prefix-p "id:" heading)
      (let ((position (org-find-property "ID" (substring heading 3))))
        (and position (list position)))
    (let (found)
      (org-map-entries (lambda ()
                         (when (equal (org-get-heading t t t t) heading)
                           (push (point) found))))
      (nreverse found))))

(defun org-edit--at (file heading function)
  "Call FUNCTION at the one heading HEADING names in FILE, save, and print it."
  (setq file (expand-file-name file))
  (unless (file-regular-p file) (error "no file %s" file))
  (when (string-search ".sync-conflict-" file)
    (error "%s is a Syncthing conflict copy" file))
  (when (file-equal-p file (expand-file-name "asana.org" org-directory))
    (error "asana.org is rebuilt from Asana; never edit it"))
  (let ((buffer (find-file-noselect file t)))
    (unwind-protect
        (with-current-buffer buffer
          (org-mode)
          (let ((found (org-edit--headings heading)))
            (cond
             ((null found) (error "no heading %S in %s" heading file))
             ((cdr found)
              (error "%d headings %S in %s; give its id:" (length found) heading file)))
            (goto-char (car found))
            (funcall function)
            ;; Org writes LOGBOOK entries after the command; batch has no command loop.
            (when (memq #'org-add-log-note post-command-hook)
              (org-add-log-note))
            (when (buffer-modified-p) (save-buffer))
            (goto-char (car found))
            (org-back-to-heading t)
            (princ (buffer-substring-no-properties
                    (point) (save-excursion (forward-line 1)
                                            (when (looking-at-p org-planning-line-re)
                                              (forward-line 1))
                                            (point))))))
      (kill-buffer buffer))))

(defun org-edit-todo ()
  "Set the TODO state: FILE HEADING STATE."
  (pcase-let ((`(,file ,heading ,state) (org-edit--args 3 "todo FILE HEADING STATE")))
    (setq state (upcase state))
    (when (equal state "AUTO") (error "only Jon sets AUTO"))
    (org-edit--at file heading
                  (lambda ()
                    ;; Keywords are buffer-local, and a file may set its own.
                    (unless (member state org-todo-keywords-1)
                      (error "STATE is one of %s"
                             (string-join (remove "AUTO" org-todo-keywords-1) " ")))
                    (org-todo state)))))

(defun org-edit--planning (keyword usage)
  "Set or remove the KEYWORD planning date: FILE HEADING WHEN, or none."
  (pcase-let ((`(,file ,heading ,when) (org-edit--args 3 usage)))
    (org-edit--at file heading
                  (lambda ()
                    (if (equal (downcase when) "none")
                        (org-add-planning-info nil nil (intern (downcase keyword)))
                      ;; A string keeps the time and cookies.
                      (org-entry-put nil keyword (org-edit--stamp when)))))))

(defun org-edit-schedule ()
  (org-edit--planning "SCHEDULED" "schedule FILE HEADING WHEN|none"))

(defun org-edit-deadline ()
  (org-edit--planning "DEADLINE" "deadline FILE HEADING WHEN|none"))

(defun org-edit-date ()
  "Print the active timestamp for WHEN."
  (princ (concat (org-edit--stamp (car (org-edit--args 1 "date WHEN"))) "\n")))

(provide 'org-edit)
;;; org-edit.el ends here
