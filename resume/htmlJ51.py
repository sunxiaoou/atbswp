#! /usr/local/bin/python3

import re
import os
from bs4 import BeautifulSoup
from datetime import datetime
from pprint import pprint

from resume import Resume
from resume import Person
from resume import Objective
from resume import Experience
from resume import Project
from resume import Education


class HtmlJ51:
    type = 'j51'
    soup = None
    timestamp = None
    skills = []

    @staticmethod
    def get_type():
        return HtmlJ51.type

    @staticmethod
    def get_timestamp(file):
        try:
            tag = HtmlJ51.soup.body.find(id='lblResumeUpdateTime')
            mo = re.compile(r'(\d{4}).(\d\d).(\d\d)').search(tag.getText())
            date = datetime(int(mo.group(1)), int(mo.group(2)), int(mo.group(3)))
        except AttributeError:
            date = datetime.fromtimestamp(os.path.getmtime(file))
        return date

    @staticmethod
    def get_objective():
        tag = HtmlJ51.soup.find('td', text='求职意向').find_next('table')
        if tag is None:
            return None

        tds = tag.findAll('td')

        industries = []
        try:
            for industry in re.split('，', tds[2].find('span').getText()):
                industries.append(industry)
        except (IndexError, ValueError):
            pass

        fields = []
        try:
            for field in re.split('，', tds[5].find('span').getText()):
                fields.append(field.upper())
        except (IndexError, ValueError):
            pass

        spots = []
        try:
            for spot in re.split('，', tds[3].find('span').getText()):
                spots.append(spot)
        except (IndexError, ValueError):
            pass

        salary = ''
        try:
            salaries = re.compile(r'\d+').findall(tds[4].find('span').getText())
            salary = int(salaries[-1])
        except (IndexError, ValueError):
            pass

        return Objective(spots, salary, fields, industries)

    @staticmethod
    def get_person(no):
        tag = HtmlJ51.soup.find(id='spanProcessStatusHead').find_next_sibling()
        if tag is None:
            return None

        name = re.compile(r'\w+').search(tag.getText()).group()
        if len(name) > 10:
            raise ValueError
        file = '{}_{:07d}_{}.html'.format(HtmlJ51.type, no, name)

        tag = tag.find_parent().find_parent().find_next_sibling()
        if tag is None or tag.name != 'tr':
            return None

        tds = tag.findAll('td')
        mo = re.compile(r'(\d{1,2})年.*(男|女).*(\d{4})年(\d{1,2})月', re.DOTALL).search(tds[1].getText())
        try:
            year = HtmlJ51.timestamp.year - int(mo.group(1))
        except AttributeError:
            year = ''
        gender = mo.group(2)
        birth = datetime(int(mo.group(3)), int(mo.group(4)), 15)
        if tds[7].getText() == '电　话：':
            i = 8
        else:
            i = 10
        phone = re.compile(r'\d{11}').search(tds[i].getText()).group()

        try:
            email = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}').search(tds[i + 2].getText()).group()
        except (AttributeError, IndexError):
            email = ''

        try:
            tag = HtmlJ51.soup.find(text='最高学历').find_next('td').find_next('td')
            education = Education.educationList.index(tag.getText().upper()) + 1
        except (AttributeError, ValueError):
            education = ''

        return Person(file, HtmlJ51.timestamp, name, gender, birth, phone, email, education, '', year,
                      HtmlJ51.get_objective())

    @staticmethod
    def get_experiences():
        try:
            tag = HtmlJ51.soup.find('td', text='工作经验').find_next('table')
        except AttributeError:
            return []

        tds = tag.findAll('td')

        experiences = []
        j = 0
        date1 = date2 = company = company_desc = job = job_desc = ''
        for i in range(len(tds)):
            if j == 0:
                text = re.sub(r'[\s\n]', '', tds[i].getText())
                mo = re.compile(r'(\d{4}).*/(\d{1,2}).*((\d{4}).*/(\d{1,2})|至今)：(\w+)', re.DOTALL).search(text)
                date1 = datetime(int(mo.group(1)), int(mo.group(2)), 15)
                if '至今' != mo.group(3):
                    date2 = datetime(int(mo.group(4)), int(mo.group(5)), 15)
                else:
                    date2 = HtmlJ51.timestamp
                company = mo.group(6)
            elif j == 2:
                company_desc = tds[i].getText()
            elif j == 4:
                job = tds[i].getText()
            elif j == 5:
                job_desc = tds[i].getText()
                experiences.append(Experience(date1, date2, company, company_desc, job, job_desc))
                date1 = date2 = company = company_desc = job = job_desc = ''
            elif j > 5:
                if not tds[i].getText():
                    j = -1      # to zero
            j += 1

        return experiences

    @staticmethod
    def get_projects():
        try:
            tag = HtmlJ51.soup.find('td', text='项目经验').find_next('table')
        except AttributeError:
            return []

        tds = tag.findAll('td')

        projects = []
        j = 0
        date1 = date2 = name = description = duty = ''
        for i in range(len(tds)):
            if j == 0:
                text = re.sub(r'[\s\n]', '', tds[i].getText())
                mo = re.compile(r'(\d{4}).*/(\d{1,2}).*((\d{4}).*/(\d{1,2})|至今)：\W*(\w+)', re.DOTALL).search(text)
                date1 = datetime(int(mo.group(1)), int(mo.group(2)), 15)
                if '至今' != mo.group(3):
                    date2 = datetime(int(mo.group(4)), int(mo.group(5)), 15)
                else:
                    date2 = HtmlJ51.timestamp
                name = mo.group(6)
            elif j == 1:
                if tds[i].getText() == '项目描述：':
                    j += 2
            elif j == 2:
                HtmlJ51.skills.append(tds[i].getText())
            elif j == 4:
                description = tds[i].getText()
            elif j == 6:
                duty = tds[i].getText()
                projects.append(Project(date1, date2, name, description, duty))
                date1 = date2 = name = description = duty = ''
            elif j > 6:
                if not tds[i].getText():
                    j = -1      # to zero
            j += 1

        return projects

    @staticmethod
    def get_educations():
        try:
            tag = HtmlJ51.soup.find('td', text='教育经历').find_next('table')
        except AttributeError:
            return []

        tds = tag.findAll('td')

        educations = []
        j = 0
        date1 = date2 = school = major = ''
        for i in range(len(tds)):
            if j == 0:
                text = re.sub(r'[\s\n]', '', tds[i].getText())
                mo = re.compile(r'(\d{4}).*/(\d{1,2}).*((\d{4}).*/(\d{1,2})|至今)', re.DOTALL).search(text)
                date1 = datetime(int(mo.group(1)), int(mo.group(2)), 15)
                if '至今' != mo.group(3):
                    date2 = datetime(int(mo.group(4)), int(mo.group(5)), 15)
                else:
                    date2 = HtmlJ51.timestamp
            elif j == 1:
                school = tds[i].getText()
            elif j == 2:
                major = tds[i].getText()
            elif j == 3:
                try:
                    degree = Education.educationList.index(re.sub(r'[\s\n]', '', tds[i].getText()).upper()) + 1
                except ValueError:
                    degree = -1
                educations.append(Education(date1, date2, school, major, degree))
                date1 = date2 = school = major = ''
            elif j > 3:
                if not tds[i].getText():
                    j = -1      # to zero
            j += 1

        return educations

    @staticmethod
    def get_languages():
        try:
            tag = HtmlJ51.soup.find('td', text='语言能力').find_next('table')
        except AttributeError:
            return []

        string = ''
        tds = tag.findAll('td')
        for i in range(len(tds)):
            if i == 0:
                continue
            mo = re.compile(r'[^\s\n]+', re.DOTALL).search(tds[i].getText())
            if mo is not None:
                string += mo.group() + '\n'

        return string

    @staticmethod
    def get_skills():
        skills = []
        for skill in HtmlJ51.skills:
            skills += re.split(r',', skill.upper())     # merge 2 lists
        HtmlJ51.skills = []     # static variable, must clear

        return list(set(skills))        # no duplicate

    @staticmethod
    def new_resume(html, no):
        HtmlJ51.soup = BeautifulSoup(open(html), 'lxml')
        HtmlJ51.timestamp = HtmlJ51.get_timestamp(html)

        person = HtmlJ51.get_person(no)
        experiences = HtmlJ51.get_experiences()
        projects = HtmlJ51.get_projects()
        educations = HtmlJ51.get_educations()
        languages = HtmlJ51.get_languages()
        skills = HtmlJ51.get_skills()

        return Resume(person, experiences, projects, educations, languages, skills)


def main():
    folder = os.path.join('/home/xixisun/suzy/shoulie/resumes', HtmlJ51.type)
    file = 'j51_0024167_王强.html'
    # file = 'j51_0014624_李智惠.html'
    resume = HtmlJ51.new_resume(os.path.join(folder, file), 4)
    pprint(resume.to_dictionary(False))

if __name__ == "__main__":
    main()
