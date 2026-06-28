import json

from academic_os.interfaces.cli import main


def test_cli_import_list_and_show_workflow(
    tmp_path,
    capsys,
    monkeypatch,
) -> None:
    database_path = tmp_path / "cli-test.db"
    database_url = f"sqlite:///{database_path.as_posix()}"
    source = tmp_path / "curriculum.json"
    source.write_text(
        json.dumps(
            {
                "items": [
                    {
                        "id": "DP-01",
                        "parent_id": None,
                        "type": "chapter",
                        "course": "פסיכולוגיה התפתחותית",
                        "source": "כרך א",
                        "title": "מבוא",
                        "pages": "1-10",
                    }
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    assert main(["--database-url", database_url, "init-db"]) == 0
    capsys.readouterr()

    assert (
        main(
            [
                "--database-url",
                database_url,
                "import-curriculum",
                str(source),
            ]
        )
        == 0
    )
    import_output = capsys.readouterr().out
    assert "Imported 1 courses and 1 curriculum items." in import_output

    assert main(["--database-url", database_url, "list-courses"]) == 0
    course_output = capsys.readouterr().out
    assert "פסיכולוגיה התפתחותית" in course_output

    assert (
        main(
            [
                "--database-url",
                database_url,
                "show-item",
                "DP-01",
            ]
        )
        == 0
    )
    item_output = capsys.readouterr().out
    assert "[DP-01] מבוא" in item_output
    assert "Pages: 1-10" in item_output
    assert "Next: academic-os create-default-tasks DP-01" in item_output

    assert (
        main(
            [
                "--database-url",
                database_url,
                "create-default-tasks",
                "DP-01",
            ]
        )
        == 0
    )
    task_output = capsys.readouterr().out
    first_task_id = task_output.splitlines()[0].split("\t")[0]

    assert (
        main(
            [
                "--database-url",
                database_url,
                "complete-task",
                first_task_id,
            ]
        )
        == 0
    )
    assert "Completed task" in capsys.readouterr().out

    assert (
        main(
            [
                "--database-url",
                database_url,
                "add-note",
                "DP-01",
                "הערה",
            ]
        )
        == 0
    )
    assert "Added note" in capsys.readouterr().out

    assert (
        main(
            [
                "--database-url",
                database_url,
                "log-session",
                "DP-01",
                "--minutes",
                "30",
            ]
        )
        == 0
    )
    assert "Logged 30 minutes" in capsys.readouterr().out

    assert (
        main(
            [
                "--database-url",
                database_url,
                "set-progress",
                "DP-01",
                "in_progress",
            ]
        )
        == 0
    )
    assert "Progress for DP-01: in_progress" in capsys.readouterr().out

    assert (
        main(
            ["--database-url", database_url, "show-item", "DP-01"]
        )
        == 0
    )
    updated_output = capsys.readouterr().out
    assert "Progress: in_progress" in updated_output
    assert "[done] reading: Reading" in updated_output
