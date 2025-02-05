import sys
import os
import datetime
import zipfile
import io
import requests
import codegrade as cg
from fpdf import FPDF
from dotenv import load_dotenv
load_dotenv()


# logs into codegrade
def login(username, password):
    try:
        client = cg.login(
            username=username,
            password=password,
            tenant='University of Nevada, Las Vegas'
        )
        return client
    except Exception as e:
        print(e)
        raise Exception("Invalid Login")  


# gets course selected by user
def getCourse(client):
    # get courses>show all>get selection>return selection
    courses = client.course.get_all()
    for i, course in enumerate(courses):
        print("[{0}]\t{1}".format(i, course.name))
    idx = int(input("Choose Course by Above Index: "))
    return courses[idx]


# sorts array of tuples in index of passed key
def Sort_Tuple(tup, key=1):
    tup.sort(key=lambda x: x[key])
    return tup


# gets all assignment grades in passed course
def getCourseAssignmentGrades(client, course):
    assignments = []
    # get grades for each assignment
    for i in range(0, len(course.assignments)):
        assignments.append([])
        # get submissions and append each submission id/grade to array
        for s in client.assignment.get_all_submissions(assignment_id=course.assignments[i].id):
            if s.user.name.lower() != "test student":
                assignments[i].append((s.id, round(s.grade, 2)))
    # sort each list of assignments ascending
    for i in range(len(assignments)):
        assignments[i] = Sort_Tuple(assignments[i])

    return assignments


# gets min/mid/max of passed assignments
def getMinMedMaxAssignments(assignments):
    howMany = int(input("How many sections is a record needed for? "))
    stats = []
    # find for each assignment
    for i in range(len(assignments)):
        # skip 0's
        min = 0
        mid = int(len(assignments[i])/2-1)
        max = len(assignments[i])-1
        while (assignments[i][min][1] == 0):
            min += 1
        # min/mid/max
        stats.append([])
        for j in range(howMany):
            stats[i].append((
                assignments[i][min+j if min+j < len(assignments[i]) else min],
                assignments[i][mid-j if mid-j >= 0 else mid],
                assignments[i][max-j if max-j >= 0 else max]
            ))
    return stats


# creates ABET report for passed submission
def createPDF(name, client, submission):
    # get zip file for submission
    client.http.timeout = None
    submission_zip = client.submission.get(
        submission_id=submission.id, type='zip')
    zip_file = zipfile.ZipFile(io.BytesIO(
        requests.get(submission_zip.url).content))

    pdf = FPDF()
    # submission date/grade/general comments
    pdf.add_page()
    pdf.set_font("Arial", size=10)
    grading = "\nSUBMISSION DATE: {0}\nGRADE: {1}\
        \n-----------------------\nGENERAL COMMENTS\n{2}".format(
        submission.created_at, submission.grade, submission.comment)
    # concatenate rubric categories together
    res = submission.rubric_result
    for rubric, details in zip(res.rubrics, res.selected):
        grading += "\n-----------------------\n{0}\n{1}\nCATEGORY COMMENTS\
            \n{2}\nCATEGORY GRADE: {3} out of {4}".format(
            rubric.header, rubric.description, details.description,
            details.achieved_points, details.points)
    # output grading
    pdf.multi_cell(200, 10, txt=grading, align='L')
    # output each code file
    for f in zip_file.namelist():
        file = zip_file.open(f).read().decode("latin-1")
        pdf.add_page()
        pdf.set_font("Arial", size=10, style="BU")
        pdf.multi_cell(200, 10, txt="{0}".format(f), align='L')
        pdf.set_font("Courier", size=8)
        pdf.multi_cell(200, 10, txt="{0}".format(file), align='L')
    pdf.output(name)  # save


# creates report for all assignments in single directory
def createReport(client, stats):
    # create directory for report
    parentDirectory = os.getcwd()
    for i in range(len(stats[0])):
        print("Running Section 1{0} Record...".format(str(i+1).zfill(3)))
        directory = str(i+1) + "_" + datetime.datetime.now().strftime("%m_%d_%Y")
        #directory = str("1{0}_ABET Assignment Record {1}".format(
            #str(i+1).zfill(3), datetime.datetime.now()))
        coursePath = os.path.join(parentDirectory, directory)
        os.mkdir(coursePath)
        # run report for each assignment
        for assignmentNum in range(len(stats)):
            print("Running Assignment {0} Record...".format(assignmentNum))
            assignmentPath = os.path.join(
                coursePath, "Assignment {0}".format(assignmentNum))
            os.mkdir(assignmentPath)
            # min/mid/max for assignment
            for k in range(len(stats[assignmentNum][i])):
                filePath = "{0}/{1}".format(assignmentPath, "min.pdf" if k ==
                                            0 else ("mid.pdf" if k == 1 else "max.pdf"))
                createPDF(filePath, client,
                          client.submission.get(submission_id=stats[assignmentNum][i][k][0]))


if __name__ == "__main__":
    # login>get course>get assigments>get min/mid/max>create pdfs
    f = open(".env")
    line = f.read().split(' ')
    f.close()
    #client = login(os.getenv("USERNAME"), os.getenv("PASSWORD"))
    client = login(line[0], line[1])
    createReport(client, getMinMedMaxAssignments(
        getCourseAssignmentGrades(client, getCourse(client))))
